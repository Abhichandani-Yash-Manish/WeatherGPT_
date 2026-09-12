"""Controlled Hindi/Gujarati forecast wording; numbers remain tool-owned."""
TEXT={
 'gu':{'intro':'પસંદ કરેલા સ્થળ માટે મોડેલની આગાહી:', 'rain':'વરસાદની અંદાજિત માત્રા','temp':'તાપમાનના કલાકવાર નમૂનાઓ','humidity':'સાપેક્ષ ભેજ','wind':'પવનની ઝડપ',
       'scope':'આ પસંદ કરેલા સ્થળ-બિંદુ માટે મોડેલની આગાહી છે, સ્થળ પરનું અવલોકન કે આખા જિલ્લાની સરેરાશ નથી. આગાહી બદલાઈ શકે છે.',
       'partial':'પ્રશ્નના કેટલાક ભાગો માટે જરૂરી માહિતી ઉપલબ્ધ નથી. નીચેની મર્યાદાઓ જુઓ.'},
 'hi':{'intro':'चुने हुए स्थान के लिए मॉडल का पूर्वानुमान:', 'rain':'वर्षा की अनुमानित मात्रा','temp':'तापमान के घंटेवार नमूने','humidity':'सापेक्ष आर्द्रता','wind':'हवा की गति',
       'scope':'यह चुने हुए स्थान-बिंदु के लिए मॉडल का पूर्वानुमान है, वहाँ मापा गया अवलोकन या पूरे जिले का औसत नहीं। पूर्वानुमान बदल सकता है।',
       'partial':'प्रश्न के कुछ हिस्सों के लिए आवश्यक जानकारी उपलब्ध नहीं है। नीचे दी गई सीमाएँ देखें।'}}

def forecast_text(result):
    lang=result['plan']['language'].lower().split('-')[0]
    if lang not in TEXT or result['plan']['intent']!='forecast' or not result['facts']:return None
    t=TEXT[lang];lines=[t['intro']];previous=None
    labels={'Forecast rainfall':t['rain'],'Temperature samples':t['temp'],'Humidity samples':t['humidity'],'Wind samples':t['wind']}
    for f in result['facts']:
        window=(f['place'],f['start'],f['end'])
        if window!=previous:
            lines.append(f"{f['place']} · {f['start'][:10]} {f['start'][11:16]} → {f['end'][:10]} {f['end'][11:16]} IST")
            previous=window
        lines.append(f"{labels.get(f['label'],f['label'])}: {f['value']} {f['unit']} [{f['id']}]")
    lines.append(t['scope'])
    if result['status']=='partial':lines.append(t['partial'])
    return '\n'.join(lines)
