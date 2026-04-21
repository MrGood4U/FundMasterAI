from daos.example_dao import ExampleDao


class ExampleService:
    def __init__(self):
        self.dao = ExampleDao()

    def get_example_detail(self, example_id: int):
        record = self.dao.get_by_id(example_id)
        if record is None:
            return None

        return {
            "id": record["id"],
            "name": record["name"],
            "risk_level": record["risk_level"],
            "summary": f"Fund {record['name']} is a {record['risk_level']} risk product.",
        }
