from workload_intelligence.specs import load_spec


def _ontology_primitives() -> set[str]:
    ontology = load_spec("primitive-ontology.yaml")["PrimitiveIntent"]
    return {
        primitive
        for group in ontology.values()
        for primitive in group
    }


def test_primitive_ontology_describes_every_primitive():
    spec = load_spec("primitive-ontology.yaml")
    descriptions = spec["PrimitiveDescriptions"]

    assert set(descriptions) == _ontology_primitives()
    assert all(descriptions[primitive].strip() for primitive in descriptions)


def test_sprint_zero_specs_include_required_acceptance_cases():
    cases = {case["case"] for case in load_spec("test-cases.yaml")["cases"]}

    assert {
        "elastic_dashboard_query",
        "elastic_text_search",
        "redis_cache_get_setex",
        "redis_durable_state_get_set_without_ttl",
        "postgres_simple_oltp_lookup",
        "postgres_scan_group_by",
        "postgres_text_search_catalog",
    }.issubset(cases)


def test_primitive_rules_preserve_evidence_and_confidence():
    rules = load_spec("primitive-rules.yaml")["rules"]

    assert rules
    assert all("evidence" in rule for rule in rules)
    assert all("rule_confidence" in rule for rule in rules)
    assert all("signal_weight" in rule for rule in rules)


def test_primitive_rules_use_only_ontology_primitives():
    ontology_primitives = _ontology_primitives()
    rule_primitives = {
        rule["primitive"]
        for rule in load_spec("primitive-rules.yaml")["rules"]
    }

    assert rule_primitives <= ontology_primitives


def test_simulator_capabilities_use_only_ontology_primitives():
    ontology_primitives = _ontology_primitives()
    capabilities = load_spec("simulator-capabilities.yaml")["platforms"]
    referenced: set[str] = set()

    for capability in capabilities.values():
        referenced.update(capability.get("supported_primitives") or [])
        referenced.update((capability.get("unsupported_primitives") or {}).keys())
        referenced.update(capability.get("response_derived_primitives") or [])
        for combination in capability.get("unsupported_combinations") or []:
            referenced.update(combination.get("primitives") or [])

    assert referenced <= ontology_primitives
