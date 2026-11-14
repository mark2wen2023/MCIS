"""Pure integration, synthetic source state only: no ORM/current DB claim."""
from copy import deepcopy
from pathlib import Path
import importlib.util,sys
from binding import build,validate,digest,BindingError
import pytest


def test_public_pdf_current_source_hash_preserved_on_success_and_failure():
    root=Path(__file__).resolve().parents[2]
    p=root/'reports/yangze22/report.pdf';raw=p.read_bytes()
    spec=importlib.util.spec_from_file_location('combined_pdf_deriver',root/'tests_acceptance/PDF_TEXT_LAYER_CANDIDATE/derive.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    state={'currentSha256':digest(raw),'registeredSha256':digest(raw),'custodyEvents':[]}
    original=deepcopy(state)
    binding={'caseId':'OFFLINE-PUBLIC','evidenceId':'SYNTHETIC-ID','registeredSha256':state['registeredSha256'],'expectedCurrentSha256':state['currentSha256'],'sourceStateDigest':digest(b'synthetic state')}
    frozen=deepcopy(binding)
    derivative=module.derive(raw);artifact=build(binding,raw,derivative)
    assert validate(artifact,binding,raw)
    assert state==original and binding==frozen and p.read_bytes()==raw
    bad=deepcopy(derivative);bad['sourcePdfSha256']=artifact['derivativeContentSha256']
    with pytest.raises(BindingError):build(binding,raw,bad)
    assert state==original and binding==frozen and p.read_bytes()==raw
