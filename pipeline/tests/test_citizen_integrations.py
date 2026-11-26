import hashlib
import hmac
from lake_protect.integrations.citizen import normalize_meta_webhook, verify_meta_signature, classify_report

def test_meta_signature_requires_valid_hmac():
    body=b'{"object":"whatsapp_business_account"}'; secret="test-secret"
    sig="sha256="+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    assert verify_meta_signature(body,sig,secret)
    assert not verify_meta_signature(body,"sha256=bad",secret)
    assert not verify_meta_signature(body,None,secret)

def test_normalize_whatsapp_location_and_dedupe_fingerprint():
    payload={"entry":[{"changes":[{"value":{"messages":[
        {"id":"wamid.1","from":"919999999999","timestamp":"1795640000","type":"location",
         "location":{"latitude":17.3,"longitude":78.4,"name":"Lake edge"}}]}}]}]}
    a=normalize_meta_webhook(payload)[0]; b=normalize_meta_webhook(payload)[0]
    assert (a.latitude,a.longitude)==(17.3,78.4)
    assert a.fingerprint==b.fingerprint and a.trust=="UNVERIFIED"
    assert a.sender_ref!="919999999999"

def test_keyword_hints_are_non_authoritative():
    assert "land_filling" in classify_report("soil dumping near lake")
