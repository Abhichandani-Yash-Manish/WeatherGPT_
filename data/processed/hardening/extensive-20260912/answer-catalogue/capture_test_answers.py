import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
root=Path('/Users/heer/WeatherGPT');sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests'))
from weathergpt_data.answers import AnswerService
out=root/'data/processed/hardening/extensive-20260912/answer-catalogue'
records=[];active={'test':None};original=AnswerService.answer
class Result(unittest.TextTestResult):
 def startTest(self,test):active['test']=test.id();super().startTest(test)
def captured(self,question,**selection):
 result=original(self,question,**selection)
 records.append({'case_number':len(records)+1,'test':active['test'],'evidence_mode':'automated_test_fixture','selection':copy.deepcopy(selection),'response':copy.deepcopy(result)})
 return result
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
with (out/'capture-tests.txt').open('w') as stream,patch.object(AnswerService,'answer',captured):
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
(out/'automated-test-answers.json').write_text(json.dumps(records,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
summary={'tests_run':result.testsRun,'tests_passed':result.wasSuccessful(),'answer_responses_captured':len(records),'tests_producing_answers':len({r['test'] for r in records}),'note':'New offline capture of actual automated test responses; synthetic fixture values are not weather observations or live forecasts.'}
(out/'capture-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if not result.wasSuccessful():raise SystemExit(1)
