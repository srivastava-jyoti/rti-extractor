"""The generated prompt, schema and labels must follow the config, not code."""

from rti_extractor.extract.prompts import build_prompt
from rti_extractor.extract.schema import build_answers_model
from rti_extractor.rti_type import get_rti_type


def test_schema_fields_come_from_the_config() -> None:
    rti_type = get_rti_type("annual-budget")
    model = build_answers_model(rti_type)
    assert list(model.model_fields) == [field.name for field in rti_type.fields]


def test_schema_is_cached() -> None:
    rti_type = get_rti_type("annual-budget")
    assert build_answers_model(rti_type) is build_answers_model(rti_type)


def test_prompt_lists_every_question_in_order() -> None:
    rti_type = get_rti_type("annual-budget")
    prompt = build_prompt(rti_type)
    for position, field in enumerate(rti_type.fields, start=1):
        assert f"{position}. {field.name} - {field.question}" in prompt


def test_prompt_carries_type_specific_rules() -> None:
    rti_type = get_rti_type("annual-budget")
    prompt = build_prompt(rti_type)
    for rule in rti_type.extra_rules:
        assert rule in prompt


def test_labels_are_numbered_from_one() -> None:
    rti_type = get_rti_type("annual-budget")
    labels = rti_type.labels
    assert list(labels) == [field.name for field in rti_type.fields]
    assert labels[rti_type.fields[0].name].startswith("1. ")


def test_strapi_names_derive_from_the_collection() -> None:
    rti_type = get_rti_type("annual-budget")
    assert rti_type.singular == "annual-budget"
    assert rti_type.api_uid == "api::annual-budget.annual-budget"
    assert rti_type.relation_field == "annual_budget"
