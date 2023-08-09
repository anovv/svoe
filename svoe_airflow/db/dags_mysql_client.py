from typing import Optional, Dict, Tuple, List

from common.db.mysql_client import MysqlClient, Session
from svoe_airflow.db.models import DagConfigEncoded
from common.common_utils import base64_decode


class DagsMysqlClient(MysqlClient):
    def __init__(self, config: Optional[Dict] = None):
        super(DagsMysqlClient, self).__init__(config=config)

    def save_db_config_encoded(
        self,
        owner_id: str,
        dag_name: str,
        dag_config_encoded: str
    ):
        item = DagConfigEncoded(
            owner_id=owner_id,
            dag_name=dag_name,
            dag_config_encoded=dag_config_encoded,
        )
        session = Session()
        session.add(item)
        session.commit()

    def select_all_configs(self) -> List[Tuple[str, str, Dict]]:# owner_id, dag_name, decoded_config
        records: List[DagConfigEncoded] = DagConfigEncoded.query.all()
        res = []
        for r in records:
            res.append(r.owner_id)
            res.append(r.dag_name)
            res.append(base64_decode(r.dag_config_encoded))

        return res
