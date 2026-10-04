import unittest

from dualsense_battery import config
from dualsense_battery.reader import parse_report
from dualsense_battery.triggers import should_show


def report(rid, ps_idx, st_idx, ps=False, status=0x08, size=78):
    data = [0] * size
    data[0] = rid
    data[ps_idx] = 1 if ps else 0
    data[st_idx] = status
    return data


class ParseReportTests(unittest.TestCase):
    def test_usb(self):
        self.assertEqual(parse_report(report(0x01, 10, 53, ps=True, status=0x07)),
                         (True, 75, "discharging"))

    def test_bluetooth(self):
        self.assertEqual(parse_report(report(0x31, 11, 54, ps=False, status=0x0A)),
                         (False, 100, "discharging"))

    def test_charging_and_full(self):
        self.assertEqual(parse_report(report(0x31, 11, 54, status=0x13))[1:], (35, "charging"))
        self.assertEqual(parse_report(report(0x31, 11, 54, status=0x2A))[1:], (100, "full"))

    def test_unknown_or_short(self):
        self.assertIsNone(parse_report([]))
        self.assertIsNone(parse_report([0x01] * 10))
        self.assertIsNone(parse_report(report(0x07, 11, 54)))


class ConfigTests(unittest.TestCase):
    def test_defaults_when_garbage(self):
        cfg = config.sanitize({"scale": "abc", "corner": "nowhere", "style": 5, "accent": "red",
                               "monitor": "x", "low_threshold": 999})
        self.assertEqual(cfg["scale"], config.DEFAULTS["scale"])
        self.assertEqual(cfg["corner"], "top-right")
        self.assertEqual(cfg["style"], "ring")
        self.assertEqual(cfg["accent"], config.DEFAULTS["accent"])
        self.assertEqual(cfg["monitor"], "primary")
        self.assertEqual(cfg["low_threshold"], 50)

    def test_clamps_and_monitor_index(self):
        cfg = config.sanitize({"scale": 99, "opacity": 0, "duration": -3, "monitor": "2"})
        self.assertEqual((cfg["scale"], cfg["opacity"], cfg["duration"]), (2.5, 0.4, 1.0))
        self.assertEqual(cfg["monitor"], 2)

    def test_at_least_one_trigger(self):
        cfg = config.sanitize({k: False for k in config.TRIGGERS})
        self.assertTrue(cfg["on_ps"])


class TriggerTests(unittest.TestCase):
    base = dict(config.DEFAULTS)

    def cfg(self, **kw):
        return {**self.base, **{k: False for k in config.TRIGGERS}, **kw}

    def test_ps_and_connect(self):
        self.assertTrue(should_show("ps", 50, "discharging", None, self.cfg(on_ps=True)))
        self.assertFalse(should_show("ps", 50, "discharging", None, self.cfg(on_connect=True)))
        self.assertTrue(should_show("connect", 50, "discharging", None, self.cfg(on_connect=True)))

    def test_charge_events(self):
        cfg = self.cfg(on_charge=True)
        self.assertTrue(should_show("change", 55, "charging", (55, "discharging"), cfg))
        self.assertTrue(should_show("change", 100, "full", (95, "charging"), cfg))
        self.assertFalse(should_show("change", 65, "charging", (55, "charging"), cfg))

    def test_low_battery(self):
        cfg = self.cfg(on_low=True, low_threshold=20)
        self.assertTrue(should_show("change", 15, "discharging", (25, "discharging"), cfg))
        self.assertFalse(should_show("change", 25, "discharging", (35, "discharging"), cfg))
        self.assertFalse(should_show("change", 15, "charging", (5, "charging"), cfg))
        self.assertFalse(should_show("change", 15, "discharging", None, cfg))


if __name__ == "__main__":
    unittest.main()
