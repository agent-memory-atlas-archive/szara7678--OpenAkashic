import streamlit,json,platform,inspect,hashlib
from types import SimpleNamespace
from streamlit.commands.execution_control import _new_fragment_id_queue

def invoke(queue,current,scope):
    ctx=SimpleNamespace(fragment_ids_this_run=queue,current_fragment_id=current)
    try:return {'scope':scope,'input_queue':queue,'current_fragment_id':current,'outcome':'success','returned_queue':_new_fragment_id_queue(ctx,scope)}
    except Exception as e:return {'scope':scope,'input_queue':queue,'current_fragment_id':current,'outcome':'error','error_type':type(e).__name__,'error':str(e)}
source=inspect.getsource(_new_fragment_id_queue)
print(json.dumps({'package':'streamlit','version':streamlit.__version__,'python':platform.python_version(),'level':'installed private guard unit probe with minimal context; no Streamlit UI/session execution','guard_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'observations':[{'id':'streamlit-full-run-fragment-guard','observations':[invoke([], 'inside-decorated-fragment','fragment'),invoke([], 'inside-decorated-fragment','app')]},{'id':'streamlit-fragment-run-queue','observations':[invoke(['earlier','current','later'],'current','fragment'),invoke(['earlier','current','later'],'current','app')]}]},indent=2))
