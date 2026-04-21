class ExampleDao:
    # Simulates rows from a DB table.
    _EXAMPLE_DATA = {
        1: {"id": 1, "name": "Growth Alpha", "risk_level": "high"},
        2: {"id": 2, "name": "Stable Bond", "risk_level": "low"},
        3: {"id": 3, "name": "Balanced Core", "risk_level": "medium"},
    }

    def get_by_id(self, example_id: int):
        return self._EXAMPLE_DATA.get(example_id)
