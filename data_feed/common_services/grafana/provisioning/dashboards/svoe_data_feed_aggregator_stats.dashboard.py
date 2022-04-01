# generate-dashboard -o svoe_data_feed_aggregator_stats.json svoe_data_feed_aggregator_stats.dashboard.py
from grafanalib.core import (
    OPS_FORMAT, Row, Dashboard, Graph,
    single_y_axis, Target, YAxis, MILLISECONDS_FORMAT, MINUTES_FORMAT
)

from grafanalib.prometheus import PromGraph


dashboard = Dashboard(
    title="Data Feed Aggregator Metrics",
    description="Latency and counters for aggregator operations and upload object sizes",
    timezone="browser",
    rows=[
        Row(
            panels=[
                PromGraph(
                    title="Read event counter",
                    data_source='Prometheus',
                    expressions=[
                        ('1m window', '60 * rate(svoe_latency_ms_histogram_count{operation=\'read\'}[1m])'),
                    ],
                    yAxes=[
                        YAxis(format=OPS_FORMAT),
                        YAxis(format=MINUTES_FORMAT),
                    ],
                ),
                PromGraph(
                    title="Write event counter",
                    data_source='Prometheus',
                    expressions=[
                        ('1m window', '60 * rate(svoe_latency_ms_histogram_count{operation=\'write\'}[1m])'),
                    ],
                    yAxes=[
                        YAxis(format=OPS_FORMAT),
                        YAxis(format=MINUTES_FORMAT),
                    ],
                ),
                # Graph(
                #     title="Read event counter",
                #     dataSource='Prometheus',
                #     targets=[
                #         Target(
                #             expr='rate(svoe_latency_ms_histogram_count{operation=\'read\'}[1m])',
                #             legendFormat="{{ handler }}",
                #             refId='A',
                #         ),
                #     ],
                #     yAxes=single_y_axis(format=OPS_FORMAT),
                # ),
            ],
        ),
    ]
).auto_panel_ids()