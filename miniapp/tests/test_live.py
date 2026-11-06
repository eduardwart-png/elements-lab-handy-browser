import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('elements_live', ROOT / 'live.py')
assert spec is not None and spec.loader is not None
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)

class Process:
    def __init__(self, code=None): self.code = code
    def poll(self): return self.code

class LiveRecoveryContract(unittest.TestCase):
    def test_tunnel_parser_ignores_service_api_and_accepts_only_https_tunnel(self):
        self.assertEqual(live.tunnel_url('Visit https://api.trycloudflare.com then https://working-shop.trycloudflare.com'), 'https://working-shop.trycloudflare.com')
        self.assertEqual(live.tunnel_url('http://not-a-tunnel.invalid'), '')

    def test_supervisor_keeps_the_mac_awake_and_reports_the_power_source(self):
        self.assertEqual(live.KEEP_AWAKE[0], '/usr/bin/caffeinate')
        self.assertIn('-s', live.KEEP_AWAKE)   # kein Systemschlaf am Netzteil, auch bei geschlossenem Deckel
        proc = live.keep_awake()
        try:
            self.assertIsNotNone(proc)
            self.assertIsNone(proc.poll())
        finally:
            if proc:
                proc.terminate()
                proc.wait(timeout=5)
        self.assertIn(live.power_source(), {'ac', 'battery', 'unknown'})

    def test_exited_bot_is_restarted_and_public_failure_requires_six_probes(self):
        processes = {'tunnel': Process(), 'server': Process(), 'bot': Process(1)}
        reason, failures = live.restart_reason(processes, 'https://x.trycloudflare.com', lambda u: True, 0)
        self.assertEqual(reason, 'bot exited')
        processes['bot'] = Process()
        failures = 0
        self.assertEqual(live.UNHEALTHY_LIMIT, 6)
        for _ in range(5):
            reason, failures = live.restart_reason(processes, 'https://x.trycloudflare.com', lambda u: False, failures)
            self.assertEqual(reason, '')
        reason, failures = live.restart_reason(processes, 'https://x.trycloudflare.com', lambda u: False, failures)
        self.assertEqual(reason, 'public endpoint unhealthy')
        self.assertEqual(live.restart_reason(processes, 'https://x.trycloudflare.com', lambda u: True, failures), ('', 0))

if __name__ == '__main__': unittest.main()
