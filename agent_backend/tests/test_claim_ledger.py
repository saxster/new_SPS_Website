from skills.claim_ledger import ClaimLedger


def test_claim_ledger_numeric_claims():
    ledger = ClaimLedger()
    draft = {
        "body": "A system reduced incidents by 25% in 2024. [S1]\n\nAnother paragraph.",
        "regulations": []
    }
    evidence = [{"id": "S1", "domain": "example.com"}]
    result = ledger.build(draft, evidence)
    assert result["metrics"]["claim_count"] >= 1
    assert result["metrics"]["numeric_claims"] >= 1


def test_claim_ledger_regulatory_claims():
    ledger = ClaimLedger()
    draft = {
        "body": "The National Building Code 2016 mandates fire exits. [S1]",
        "regulations": ["National Building Code 2016"]
    }
    evidence = [{"id": "S1", "domain": "egazette.nic.in"}]
    result = ledger.build(draft, evidence)
    assert result["metrics"]["regulatory_claims"] >= 1
