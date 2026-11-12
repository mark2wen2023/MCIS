from pathlib import Path
import os
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
st=Settings();st.seed_demo=False
app=create_app(st)
with app.state.db.session() as s: seed(s, st.blob_dir)
