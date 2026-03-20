from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocFieldSpec(BaseModel):
    required: bool = False
    description: str | None = None


class DocTypeSpec(BaseModel):
    title: str
    aliases: list[str] = Field(default_factory=list)
    fields: dict[str, DocFieldSpec] = Field(default_factory=dict)


class RequirementRule(BaseModel):
    entity_type: str
    products_any: list[str] = Field(default_factory=list)
    risk_tiers_any: list[str] = Field(default_factory=list)
    required_docs: list[str] = Field(default_factory=list)


class CountryRules(BaseModel):
    country: str
    version: str = "1"
    doc_types: dict[str, DocTypeSpec]
    requirements: list[RequirementRule]

    def required_docs_for(self, *, entity_type: str, products: list[str], risk_tier: str) -> list[str]:
        et = entity_type.lower()
        rt = risk_tier.lower()
        prods = {p.lower() for p in products}
        required: list[str] = []
        for r in self.requirements:
            if r.entity_type.lower() != et:
                continue
            if r.risk_tiers_any and rt not in {x.lower() for x in r.risk_tiers_any}:
                continue
            if r.products_any and not (prods & {x.lower() for x in r.products_any}):
                continue
            required.extend(r.required_docs)
        # stable unique
        seen: set[str] = set()
        out: list[str] = []
        for d in required:
            if d not in seen:
                seen.add(d)
                out.append(d)
        return out

