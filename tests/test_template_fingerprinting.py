from workload_intelligence.normalize.template_fingerprint import fingerprint_query


def test_elasticsearch_templates_ignore_literal_values():
    first = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"customer_id": 123}},
                    {"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}},
                ]
            }
        },
        "aggs": {"by_status": {"terms": {"field": "status"}}},
    }
    second = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"customer_id": 456}},
                    {"range": {"@timestamp": {"gte": "now-2h", "lte": "now"}}},
                ]
            }
        },
        "aggs": {"by_status": {"terms": {"field": "status"}}},
    }

    assert fingerprint_query(first)["template_id"] == fingerprint_query(second)["template_id"]
    assert fingerprint_query(first)["normalized_query"]["query"]["bool"]["filter"][0]["term"]["customer_id"] == "?"


def test_structural_aggregation_field_remains_in_template():
    query = {"aggs": {"by_status": {"terms": {"field": "status"}}}}

    assert fingerprint_query(query)["normalized_query"]["aggs"]["by_status"]["terms"]["field"] == "status"

