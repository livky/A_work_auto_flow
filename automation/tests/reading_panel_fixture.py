"""通过公开动作生成阅读面板的合成数据，不直接写RS/规范memory文件。"""
import uuid
from memory.service import MemoryService
from material_query.api import dispatch
from material_query.coordinator import Coordinator


def populate(root):
    oid='RES-SYNTHETIC'
    service=MemoryService(root)
    draft={'schema_version':4,'owner_id':oid,'kind':'overview','title':'面板固定方法',
           'body_markdown':'panelreading 前提：绝对温度，偏置为273.15；这是合成展示资料，未验证现实方法。',
           'keywords':['panelreading'],'sources':[],'provenance_gap':'纯合成UI测试输入，非真实依据',
           'record_reason':'面板端到端测试','sensitivity':'internal','discovery':'workspace_summary',
           'payload':{'question':'阅读面板是否可用','methods':['查看'],'results':['待测试'],'current_stage':'合成',
                      'open_questions':[],'claims':[],'process_refs':[],'technical_refs':[],'experience_refs':[], 'limitations':['非业务结论']}}
    receipt=service.commit({'schema_version':3,'owner_id':oid,'expected_head':None,'request_id':str(uuid.uuid4()),
                            'actor':{'kind':'workflow','id':'SYNTHETIC-E2E'},'operations':[{'op':'put_record','client_key':'overview','draft':draft}]})
    assert receipt['save_status']=='committed',receipt
    app=Coordinator(root)
    try:
        template=dispatch(app,'reading-template',{})['value']
        template.update(owner_id=oid,goal='合成阅读会话',conditions=['保留单位与前提'])
        started=dispatch(app,'reading-start',template);assert started['status']=='ok',started
        revision=1
        def call(action,**fields):
            nonlocal revision
            result=dispatch(app,'reading-'+action,dict(session_id=template['session_id'],expected_revision=revision,request_id=str(uuid.uuid4()),**fields))
            assert result['status'] in {'ok','partial'},result
            revision=result['value']['revision']
            return result['value']
        recalled=call('recall',question='panelreading',keywords=[],scope=template['query']['scope'],reason='面板合成检查')
        candidate=recalled['candidates'][0]['candidate_id']
        call('read',candidate_ids=[candidate])
        call('note',candidate_id=candidate,summary='合成阅读理解：保留前提',
             connection={'kind':'direct','explanation':'核对显示的单位前提','chain':[]},
             details=[{'text':'绝对温度偏置273.15','reason':'精确数值','block_ids':[]}],uncertainties=['合成测试'])
    finally:app.close()
