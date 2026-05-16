import asyncio
import logging
import warnings
import threading
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Callable, List, Set
from intent_bus import IntentClient, WorkerRuntime, ClaimedIntent

logger = logging.getLogger("intent_bus")

def configure_observability(verbosity: str):
    """Mutes noisy tracebacks and internal warnings based on dev preference."""
    warnings.filterwarnings("ignore", category=UserWarning, module="syrin.*")
    warnings.filterwarnings("ignore", message=".*Contradiction detection.*")
    warnings.filterwarnings("ignore", message=".*No pricing data.*")

    litellm_logger = logging.getLogger("LiteLLM")
    bus_logger = logging.getLogger("intent_bus")

    if verbosity == "SILENT":
        litellm_logger.setLevel(logging.CRITICAL)
        bus_logger.setLevel(logging.CRITICAL)
    elif verbosity == "DEBUG":
        litellm_logger.setLevel(logging.DEBUG)
        bus_logger.setLevel(logging.DEBUG)
    else: # INFO
        litellm_logger.setLevel(logging.WARNING)
        bus_logger.setLevel(logging.INFO)

class ChiasmObserver:
    """A detached telemetry layer that pushes directly to a local Chiasm dashboard."""
    def __init__(self, chiasm_url: str, api_key: str, node_name: str = "worker"):
        self.url = chiasm_url.rstrip('/')
        self.api_key = api_key
        self.node_name = node_name
        self.task_map = {}

    def _send_request(self, method: str, endpoint: str, payload: dict) -> Optional[dict]:
        req = urllib.request.Request(
            f"{self.url}{endpoint}",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status in (200, 201):
                    return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            # Silently log at DEBUG level so it doesn't crash the worker but is visible if needed
            logger.debug(f"Chiasm telemetry dropped: {e}")
        return None

    def _sync_notify(self, mission_id: str, event_type: str, data: dict):
        task_id = self.task_map.get(mission_id)

        if not task_id:
            res = self._send_request("POST", "/tasks", {
                "agent": "gemini",
                "project": "Intent Bus",
                "title": f"[{self.node_name}] m:{mission_id[:8]}"
            })
            if res and 'id' in res:
                task_id = res['id']
                self.task_map[mission_id] = task_id

        if task_id and event_type in ("run_end", "error"):
            status = "completed" if event_type == "run_end" else "blocked"
            if isinstance(data, dict):
                content_key = 'content' if event_type == "run_end" else 'msg'
                raw_msg = data.get(content_key, 'Done.')
                msg = json.dumps(raw_msg, indent=2) if isinstance(raw_msg, (dict, list)) else str(raw_msg)
            else:
                msg = str(data) if data else 'Done.'

            self._send_request("PATCH", f"/tasks/{task_id}", {"status": status, "summary": msg})

    async def notify(self, mission_id: str, event_type: str, data: dict):
        await asyncio.to_thread(self._sync_notify, mission_id, event_type, data)


class SyrinMissionContext:
    def __init__(self, intent: ClaimedIntent, client: IntentClient):
        self.intent = intent
        self.client = client
        self.mission_id = intent.id
        self.parent_id = intent.payload.get('parent_mission_id')

    async def persist_state(self, state_blob: Any):
        return await asyncio.to_thread(self.client.set, f"syrin:m:{self.mission_id}:state", state_blob, ttl=86400)

    async def recover_state(self) -> Optional[Any]:
        try:
            return await asyncio.to_thread(self.client.get, f"syrin:m:{self.mission_id}:state")
        except Exception as e:
            if "not_found" in str(e).lower(): return None
            raise

    async def emit_telemetry(self, event_type: str, payload: dict):
        try:
            return await asyncio.to_thread(
                self.client.publish,
                goal=f"syrin_trace_{event_type}",
                payload={"m_id": self.mission_id, "p_id": self.parent_id, "telemetry": payload},
                namespace=self.intent.namespace
            )
        except Exception as e:
            logger.debug(f"Telemetry emit dropped ({event_type}): {e}")

    async def heartbeat(self, interval: int = 15, extension: int = 120):
        failures = 0
        try:
            while failures < 3:
                await asyncio.sleep(interval)
                try:
                    await asyncio.to_thread(self.client.extend_claim, self.mission_id, extension)
                    failures = 0
                except Exception:
                    failures += 1
        except asyncio.CancelledError:
            pass


class IntentBusSyrinHarness:
    def __init__(
        self,
        agent_factory: Callable[[], Any],
        bus: IntentClient,
        capabilities: List[str] = None,
        telemetry_filter: Set[str] = None,
        observer: Optional[ChiasmObserver] = None,
        mission_timeout: int = 900,
        node_name: str = "worker"
    ):
        self.agent_factory = agent_factory
        self.bus = bus
        self.capabilities = capabilities or []
        self.telemetry_filter = telemetry_filter or {"run_end", "error", "tool_call", "checkpoint_ready"}
        self.observer = observer
        self.mission_timeout = mission_timeout
        self.node_name = node_name

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()
        self._active_tasks: Set[asyncio.Task] = set()

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        try: self._loop.run_forever()
        finally: self._loop.close()

    def _translate_error(self, err: Any) -> str:
        err_str = str(err).lower().strip()
        if not err_str or err_str == "none": return "[Unhandled Exception] Unknown Error"
        if any(k in err_str for k in ["401", "authentication", "invalid api key", "unauthorized"]):
            return "[Authentication Failure] Invalid API key or unauthorized access. (Non-retryable)"
        if any(k in err_str for k in ["429", "rate limit", "quota", "too many requests"]):
            return "[Rate Limit Exceeded] API quota exhausted or rate limit reached. (Non-retryable)"
        if any(k in err_str for k in ["500", "502", "503", "504", "server error", "overloaded", "busy"]):
            return "[Upstream Provider Error] The model server is currently overloaded or down."
        if any(k in err_str for k in ["400", "badrequest", "not provided", "llm provider not"]):
            return "[Configuration Error] Invalid model syntax or missing provider prefix."
        if "timeout" in err_str:
            return f"[Execution Timeout] Mission exceeded the allocated {self.mission_timeout}s."
        return f"[Unhandled Exception] {str(err)}"

    async def _notify_observer_async(self, mission_id: str, event_type: str, data: Dict[str, Any]):
        if not self.observer: return
        obs_task = asyncio.create_task(self.observer.notify(mission_id, event_type, data))
        self._active_tasks.add(obs_task)
        obs_task.add_done_callback(self._active_tasks.discard)

    def _display(self, mission_id: str, tag: str, msg: str, color: str):
        colors = {"GREEN": "\033[92m", "YELLOW": "\033[93m", "CYAN": "\033[96m", "RED": "\033[91m", "RESET": "\033[0m"}
        print(f"\n[{mission_id[:8]}] [{self.node_name}] {colors.get(color, '')}{tag} {msg}{colors['RESET']}")

    async def _handle_mission(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        current_task = asyncio.current_task()
        if current_task: self._active_tasks.add(current_task)

        try:
            intent = ClaimedIntent.from_dict(envelope)
            instruction = intent.payload.get('instruction')
            if not instruction: raise ValueError("Payload missing mandatory 'instruction' key.")
            ctx = SyrinMissionContext(intent, self.bus)

            display_inst = instruction if len(instruction) < 50 else instruction[:47] + "..."
            self._display(ctx.mission_id, "⚡ MISSION RECEIVED:", display_inst, "YELLOW")

        except Exception as e:
            if current_task: self._active_tasks.discard(current_task)
            raise

        try: agent = self.agent_factory()
        except Exception as e:
            clean_msg = self._translate_error(e)
            self._display(intent.id, "🔴 MISSION FAILED:", clean_msg, "RED")
            await self._notify_observer_async(intent.id, "error", {"msg": clean_msg})
            if current_task: self._active_tasks.discard(current_task)
            raise

        heartbeat_task = asyncio.create_task(ctx.heartbeat())
        self._active_tasks.add(heartbeat_task)

        final_result = None
        fatal_error_msg = ""
        mission_failed = False

        try:
            try:
                saved_state = await ctx.recover_state()
                if saved_state and hasattr(agent, 'load_checkpoint'):
                    agent.load_checkpoint(saved_state)
            except Exception as e:
                self._display(ctx.mission_id, "🟡 [State Warning]", str(e), "YELLOW")

            async def run_mission():
                nonlocal final_result, fatal_error_msg, mission_failed
                async for event in agent.arun_events(instruction):

                    if event.type == "error":
                        raw_err = event.data.get('msg', 'Unknown Error') if isinstance(event.data, dict) else str(event.data)
                        if not str(raw_err).strip(): raw_err = "Unknown Error"
                        clean_err = self._translate_error(raw_err)
                        fatal_error_msg = clean_err
                        mission_failed = True

                        if isinstance(event.data, dict): event.data['msg'] = clean_err
                        self._display(ctx.mission_id, "🔴 MISSION FAILED:", clean_err, "RED")
                        break  # Stop processing events after error

                    if event.type in self.telemetry_filter:
                        await ctx.emit_telemetry(event.type, event.data)

                    if self.observer:
                        payload = event.data if isinstance(event.data, dict) else {"data": event.data}
                        await self._notify_observer_async(ctx.mission_id, event.type, payload)

                    if event.type == "checkpoint_ready" and hasattr(agent, 'save_checkpoint'):
                        await ctx.persist_state(agent.save_checkpoint())

                    if event.type == "run_end":
                        data = event.data
                        raw_content = data.get("content", data) if isinstance(data, dict) else data
                        final_result = json.dumps(raw_content, indent=2) if isinstance(raw_content, (dict, list)) else str(raw_content)
                        self._display(ctx.mission_id, "🟢 MISSION COMPLETE.", f"\n{final_result}\n", "CYAN")

            try:
                await asyncio.wait_for(run_mission(), timeout=self.mission_timeout)
                if mission_failed:
                    raise RuntimeError(f"Mission failed with error: {fatal_error_msg}")
                if final_result is None: raise RuntimeError("Mission generator exhausted without 'run_end'.")
                return {'result': final_result, 'result_type': 'text'}

            except asyncio.TimeoutError:
                clean_msg = self._translate_error("timeout")
                self._display(ctx.mission_id, "🔴 MISSION FAILED:", clean_msg, "RED")
                await self._notify_observer_async(ctx.mission_id, "error", {"msg": clean_msg})
                raise

            except Exception as e:
                outer_clean_msg = self._translate_error(e)
                if not fatal_error_msg or "unknown error" in fatal_error_msg.lower():
                    self._display(ctx.mission_id, "🔴 MISSION FAILED:", outer_clean_msg, "RED")
                    await self._notify_observer_async(ctx.mission_id, "error", {"msg": outer_clean_msg})
                raise

        finally:
            heartbeat_task.cancel()
            self._active_tasks.discard(heartbeat_task)
            if current_task: self._active_tasks.discard(current_task)

    def shutdown(self):
        logger.info(f"[{self.node_name}] Initiating Framework Shutdown...")
        async def _cleanup():
            current = asyncio.current_task()
            tasks = [t for t in self._active_tasks if t is not current and not t.done()]
            if tasks:
                for task in tasks: task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            if hasattr(self.bus, 'close'): self.bus.close()
            self._loop.call_soon(self._loop.stop)

        try:
            asyncio.run_coroutine_threadsafe(_cleanup(), self._loop).result(timeout=10)
        except Exception as e:
            logger.warning(f"Shutdown cleanup failed: {e}")
        if self._loop_thread.is_alive(): self._loop_thread.join(timeout=5)
        logger.info(f"[{self.node_name}] Framework terminated.")

    def serve(self, goal: str, namespace: str = "default"):
        runtime = WorkerRuntime(client=self.bus, capabilities=self.capabilities)
        def runner_bridge(envelope):
            future = asyncio.run_coroutine_threadsafe(self._handle_mission(envelope), self._loop)
            return future.result(timeout=self.mission_timeout + 30)

        try: runtime.listen(goal=goal, handler=runner_bridge, namespace=namespace, full_envelope=True)
        except KeyboardInterrupt: self.shutdown()
