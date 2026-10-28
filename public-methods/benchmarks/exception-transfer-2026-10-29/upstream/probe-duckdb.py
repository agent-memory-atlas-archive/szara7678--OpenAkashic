import duckdb,json,platform
c=duckdb.connect(':memory:')
def sql(q):
    try:return {'sql':q,'outcome':'success','rows':c.execute(q).fetchall()}
    except Exception as e:return {'sql':q,'outcome':'error','error_type':type(e).__name__,'error':str(e)}
out=[]
out.append({'id':'duckdb-implicit-varchar-function-binding','observations':[sql('SELECT substring(42,1,1)'),sql('SELECT substring(42::VARCHAR,1,1)'),sql('SET old_implicit_casting=true'),sql('SELECT substring(42,1,1)'),sql('SET old_implicit_casting=false')]})
out.append({'id':'duckdb-date-literal-varchar-boundary','observations':[sql("SELECT DATE '1992-01-01' > '1990-01-01'"),sql("SELECT DATE '1992-01-01' > '1990-01-01'::VARCHAR"),sql("SELECT DATE '1992-01-01' > s FROM (SELECT '1990-01-01'::VARCHAR AS s) t"),sql("SELECT DATE '1992-01-01' > CAST(s AS DATE) FROM (SELECT '1990-01-01'::VARCHAR AS s) t"),sql("SELECT CAST('not-a-date' AS DATE)")]})
print(json.dumps({'package':'duckdb','version':duckdb.__version__,'python':platform.python_version(),'observations':out},indent=2))
