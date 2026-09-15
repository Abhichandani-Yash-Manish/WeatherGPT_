import pathlib
p = pathlib.Path('weathergpt_data/conversation.py')
text = p.read_text()

old_guard = "        if not isinstance(body,dict) or set(body)-{'question','conversation_id','selection_id','coordinates','output_language','request_id'}:raise SourceError('Send a question and optional conversation/place/language selection')"
assert text.count(old_guard) == 1
new_guard = ("        if not isinstance(body,dict) or set(body)-{'question','conversation_id','selection_id','coordinates',"
             "'output_language','request_id','persona'}:raise SourceError('Send a question and optional conversation/place/language selection')\n"
             "        # A persona is a reading position: it is checked before any work is done and it\n"
             "        # changes no evidence, so an unknown one is refused rather than guessed.\n"
             "        from .personas import get as persona_of\n"
             "        persona_of(body.get('persona'))")
text = text.replace(old_guard, new_guard, 1)

old_save = "        state['history']=state['history'][-12:];self.save(cid,state)\n        return result"
assert text.count(old_save) == 1
new_save = ("        state['history']=state['history'][-12:];self.save(cid,state)\n"
            "        # The persona the answer was read under travels with the answer, so the framing\n"
            "        # can never be mistaken for the finding.\n"
            "        from .personas import annotate as persona_block\n"
            "        block=persona_block(body.get('persona'))\n"
            "        if block:result['persona']=block\n"
            "        return result")
text = text.replace(old_save, new_save, 1)
p.write_text(text)
print('patched')
