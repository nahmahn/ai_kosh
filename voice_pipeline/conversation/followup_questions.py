"""
Follow-up Questions — multilingual question bank for missing fields.

Provides follow-up questions in the language_of_response when fields
are missing from the initial voice extraction.

CRITICAL FIELDS (block conversation from completing):
1. enterprise_name — company/factory name
2. product_descriptions — what the MSE makes/sells
3. manufacturing_process_keywords — do they manufacture or trade
4. selling_channels — IndiaMART, Amazon, GeM, etc. OR buyer types
5. buyer_geographies_mentioned — cities/districts/export markets
6. employees_count — workforce size
7. years_in_business — tenure

OPTIONAL FIELDS (not required for completion):
8. raw_materials_mentioned — what inputs they use
"""

from typing import Dict, List, Optional

# ── Question bank ─────────────────────────────────────────────────────────────
# Each field maps to questions in multiple languages.
# Keys: field name, Values: dict of language_code → question text

FOLLOWUP_QUESTIONS: Dict[str, Dict[str, str]] = {
    "product_descriptions": {
        "hi": "Aap kya banate hain? Apne mukhya products ke baare mein batayein.",
        "en": "What do you make or sell? Please describe your main products.",
        "ta": "நீங்கள் என்ன தயாரிக்கிறீர்கள்? உங்கள் முக்கிய பொருட்களை விவரிக்கவும்.",
        "te": "మీరు ఏమి తయారు చేస్తారు? మీ ప్రధాన ఉత్పత్తులను వివరించండి.",
        "bn": "আপনি কী তৈরি করেন? আপনার প্রধান পণ্যগুলি বর্ণনা করুন।",
        "mr": "तुम्ही काय बनवता? तुमच्या मुख्य उत्पादनांबद्दल सांगा.",
        "gu": "તમે શું બનાવો છો? તમારા મુખ્ય ઉત્પાદનો વિશે જણાવો.",
        "kn": "ನೀವು ಏನು ತಯಾರಿಸುತ್ತೀರಿ? ನಿಮ್ಮ ಮುಖ್ಯ ಉತ್ಪನ್ನಗಳನ್ನು ವಿವರಿಸಿ.",
        "ml": "നിങ്ങൾ എന്താണ് ഉണ്ടാക്കുന്നത്? നിങ്ങളുടെ പ്രധാന ഉൽപ്പന്നങ്ങൾ വിവരിക്കുക.",
        "pa": "ਤੁਸੀਂ ਕੀ ਬਣਾਉਂਦੇ ਹੋ? ਆਪਣੇ ਮੁੱਖ ਉਤਪਾਦਾਂ ਬਾਰੇ ਦੱਸੋ।",
    },
    "manufacturing_process_keywords": {
        "hi": "Kya aap khud banate hain ya kharid ke bechte hain? Aap kaise banate hain?",
        "en": "Do you manufacture yourself or buy and sell? How do you make your products?",
        "ta": "நீங்கள் நேரடியாக தயாரிக்கிறீர்களா அல்லது வாங்கி விற்கிறீர்களா?",
        "te": "మీరు నేరుగా తయారు చేస్తారా లేదా కొని అమ్ముతారా?",
        "bn": "আপনি নিজে তৈরি করেন নাকি কিনে বিক্রি করেন?",
        "mr": "तुम्ही स्वतः बनवता की खरेदी करून विकता? कसे बनवता?",
        "gu": "તમે જાતે બનાવો છો કે ખરીદીને વેચો છો?",
        "kn": "ನೀವು ನೇರವಾಗಿ ತಯಾರಿಸುತ್ತೀರಾ ಅಥವಾ ಕೊಂಡು ಮಾರುತ್ತೀರಾ?",
        "ml": "നിങ്ങൾ സ്വയം ഉണ്ടാക്കുന്നോ അതോ വാങ്ങി വിൽക്കുന്നോ?",
        "pa": "ਕੀ ਤੁਸੀਂ ਖੁਦ ਬਣਾਉਂਦੇ ਹੋ ਜਾਂ ਖਰੀਦ ਕੇ ਵੇਚਦੇ ਹੋ?",
    },
    "raw_materials_mentioned": {
        "hi": "Aap kaun sa kachcha maal use karte hain? Jaise cotton, steel, lakdi?",
        "en": "What raw materials do you use? For example, cotton, steel, wood?",
        "ta": "நீங்கள் என்ன மூலப்பொருட்களை பயன்படுத்துகிறீர்கள்? உதாரணமாக பருத்தி, எஃகு?",
        "te": "మీరు ఏ ముడి పదార్థాలు ఉపయోగిస్తారు? ఉదాహరణకు పత్తి, ఉక్కు?",
        "bn": "আপনি কোন কাঁচামাল ব্যবহার করেন? যেমন তুলা, ইস্পাত, কাঠ?",
        "mr": "तुम्ही कोणता कच्चा माल वापरता? जसे कापूस, स्टील, लाकूड?",
        "gu": "તમે કયો કાચો માલ વાપરો છો? જેમ કે કપાસ, સ્ટીલ, લાકડું?",
        "kn": "ನೀವು ಯಾವ ಕಚ್ಚಾ ವಸ್ತುಗಳನ್ನು ಬಳಸುತ್ತೀರಿ? ಉದಾಹರಣೆಗೆ ಹತ್ತಿ, ಉಕ್ಕು?",
        "ml": "നിങ്ങൾ ഏതെല്ലാം അസംസ്കൃത വസ്തുക്കൾ ഉപയോഗിക്കുന്നു? ഉദാ: പരുത്തി, ഉരുക്ക്?",
        "pa": "ਤੁਸੀਂ ਕਿਹੜਾ ਕੱਚਾ ਮਾਲ ਵਰਤਦੇ ਹੋ? ਜਿਵੇਂ ਕਪਾਹ, ਸਟੀਲ, ਲੱਕੜ?",
    },
    "enterprise_name": {
        "hi": "Aapki company ya factory ka naam kya hai?",
        "en": "What is the name of your company or factory?",
        "ta": "உங்கள் நிறுவனத்தின் பெயர் என்ன?",
        "te": "మీ కంపెనీ లేదా ఫ్యాక్టరీ పేరు ఏమిటి?",
        "bn": "আপনার কোম্পানি বা কারখানার নাম কী?",
        "mr": "तुमच्या कंपनी किंवा कारखान्याचे नाव काय?",
        "gu": "તમારી કંપની અથવા ફેક્ટ્રીનું નામ શું છે?",
        "kn": "ನಿಮ್ಮ ಕಂಪನಿ ಅಥವಾ ಕಾರ್ಖಾನೆಯ ಹೆಸರೇನು?",
        "ml": "നിങ്ങളുടെ കമ്പനിയുടെ അല്ലെങ്കിൽ ഫാക്ടറിയുടെ പേര് എന്താണ്?",
        "pa": "ਤੁਹਾਡੀ ਕੰਪਨੀ ਜਾਂ ਫੈਕਟਰੀ ਦਾ ਨਾਮ ਕੀ ਹੈ?",
    },
    "buyer_types_mentioned": {
        "hi": "Aap kisko bechte hain? Retailers, wholesalers, ya seedha customers ko?",
        "en": "Who do you sell to? Retailers, wholesalers, or direct customers?",
        "ta": "நீங்கள் யாருக்கு விற்கிறீர்கள்? சில்லறை, மொத்த, அல்லது நேரடி வாடிக்கையாளர்கள்?",
        "te": "మీరు ఎవరికి విక్రయిస్తారు? రిటైలర్లు, హోల్‌సేలర్లు లేదా నేరుగా?",
        "bn": "আপনি কাকে বিক্রি করেন? খুচরা, পাইকারি, বা সরাসরি গ্রাহকদের?",
        "mr": "तुम्ही कुणाला विकता? रिटेलर्स, होलसेलर्स की डायरेक्ट?",
        "gu": "તમે કોને વેચો છો? રિટેલર્સ, હોલસેલર્સ કે ડાયરેક્ટ?",
        "kn": "ನೀವು ಯಾರಿಗೆ ಮಾರುತ್ತೀರಿ? ಮಾರಾಟಗಾರರು, ಸಗಟು ವ್ಯಾಪಾರಿಗಳು, ಅಥವಾ ನೇರ?",
        "ml": "നിങ്ങൾ ആർക്കാണ് വിൽക്കുന്നത്? ചില്ലറ, മൊത്ത, അല്ലെങ്കിൽ നേരിട്ട്?",
        "pa": "ਤੁਸੀਂ ਕਿਸਨੂੰ ਵੇਚਦੇ ਹੋ? ਰਿਟੇਲਰ, ਹੋਲਸੇਲਰ, ਜਾਂ ਸਿੱਧੇ ਗਾਹਕਾਂ ਨੂੰ?",
    },
    "buyer_geographies_mentioned": {
        "hi": "Aap kis sheher ya district mein bechte hain? Kya bahar bhi bhejte hain?",
        "en": "Which cities or districts do you sell in? Do you export as well?",
        "ta": "நீங்கள் எந்த நகரங்கள் அல்லது மாவட்டங்களில் விற்கிறீர்கள்?",
        "te": "మీరు ఏ నగరాలు లేదా జిల్లాల్లో అమ్ముతారు?",
        "bn": "আপনি কোন শহর বা জেলায় বিক্রি করেন?",
        "mr": "तुम्ही कोणत्या शहरात किंवा जिल्ह्यात विकता?",
        "gu": "તમે કયા શહેર કે જિલ્લામાં વેચો છો?",
        "kn": "ನೀವು ಯಾವ ನಗರಗಳು ಅಥವಾ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಮಾರುತ್ತೀರಿ?",
        "ml": "നിങ്ങൾ ഏത് നഗരങ്ങളിലോ ജില്ലകളിലോ വിൽക്കുന്നു?",
        "pa": "ਤੁਸੀਂ ਕਿਹੜੇ ਸ਼ਹਿਰ ਜਾਂ ਜ਼ਿਲ੍ਹੇ ਵਿੱਚ ਵੇਚਦੇ ਹੋ?",
    },
    "employees_count": {
        "hi": "Aapke yahan kitne log kaam karte hain?",
        "en": "How many people work at your business?",
        "ta": "உங்கள் தொழிலில் எத்தனை பேர் வேலை செய்கிறார்கள்?",
        "te": "మీ వ్యాపారంలో ఎంత మంది పని చేస్తారు?",
        "bn": "আপনার ব্যবসায় কতজন কাজ করে?",
        "mr": "तुमच्या व्यवसायात किती लोक काम करतात?",
        "gu": "તમારા વ્યવસાયમાં કેટલા લોકો કામ કરે છે?",
        "kn": "ನಿಮ್ಮ ವ್ಯಾಪಾರದಲ್ಲಿ ಎಷ್ಟು ಜನ ಕೆಲಸ ಮಾಡುತ್ತಾರೆ?",
        "ml": "നിങ്ങളുടെ ബിസിനസ്സിൽ എത്ര പേർ ജോലി ചെയ്യുന്നു?",
        "pa": "ਤੁਹਾਡੇ ਕਾਰੋਬਾਰ ਵਿੱਚ ਕਿੰਨੇ ਲੋਕ ਕੰਮ ਕਰਦੇ ਹਨ?",
    },
    "years_in_business": {
        "hi": "Aap kitne saalon se yeh kaam kar rahe hain?",
        "en": "How many years have you been in this business?",
        "ta": "நீங்கள் எத்தனை வருடங்களாக இத்தொழிலில் இருக்கிறீர்கள்?",
        "te": "మీరు ఎన్ని సంవత్సరాలుగా ఈ వ్యాపారంలో ఉన్నారు?",
        "bn": "আপনি কত বছর ধরে এই ব্যবসায় আছেন?",
        "mr": "तुम्ही किती वर्षांपासून हा व्यवसाय करत आहात?",
        "gu": "તમે કેટલાં વર્ષોથી આ ધંધામાં છો?",
        "kn": "ನೀವು ಎಷ್ಟು ವರ್ಷಗಳಿಂದ ಈ ವ್ಯವಹಾರದಲ್ಲಿ ಇದ್ದೀರಿ?",
        "ml": "നിങ്ങൾ എത്ര വർഷമായി ഈ ബിസിനസ്സിൽ ഉണ്ട്?",
        "pa": "ਤੁਸੀਂ ਕਿੰਨੇ ਸਾਲਾਂ ਤੋਂ ਇਹ ਕੰਮ ਕਰ ਰਹੇ ਹੋ?",
    },
    "selling_channels": {
        "hi": "Aap online bechte hain? Koi platform jaise IndiaMART, Amazon, GeM, Flipkart?",
        "en": "Do you sell online? Any platforms like IndiaMART, Amazon, GeM, Flipkart?",
        "ta": "நீங்கள் ஆன்லைனில் விற்கிறீர்களா? IndiaMART, Amazon போன்ற தளங்கள்?",
        "te": "మీరు ఆన్‌లైన్‌లో అమ్ముతారా? IndiaMART, Amazon వంటి ప్లాట్‌ఫారమ్‌లు?",
        "bn": "আপনি অনলাইনে বিক্রি করেন? IndiaMART, Amazon এর মতো প্ল্যাটফর্ম?",
        "mr": "तुम्ही ऑनलाइन विकता का? IndiaMART, Amazon सारखे प्लॅटफॉर्म?",
        "gu": "તમે ઓનલાઈન વેચો છો? IndiaMART, Amazon જેવા પ્લેટફોર્મ?",
        "kn": "ನೀವು ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಮಾರುತ್ತೀರಾ? IndiaMART, Amazon ನಂತಹ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್‌ಗಳು?",
        "ml": "നിങ്ങൾ ഓൺലൈനിൽ വിൽക്കുന്നുണ്ടോ? IndiaMART, Amazon പോലുള്ള പ്ലാറ്റ്‌ഫോമുകൾ?",
        "pa": "ਕੀ ਤੁਸੀਂ ਔਨਲਾਈਨ ਵੇਚਦੇ ਹੋ? IndiaMART, Amazon ਵਰਗੇ ਪਲੇਟਫਾਰਮ?",
    },
    "daily_production_capacity": {
        "hi": "Rozana ya mahine mein kitna maal banate hain? (Production capacity)",
        "en": "What is your daily or monthly production capacity?",
        "ta": "உங்கள் தினசரி உற்பத்தி திறன் என்ன?",
        "te": "మీ రోజువారీ ఉత్పత్తి సామర్థ్యం ఎంత?",
        "bn": "আপনার দৈনিক উৎপাদন ক্ষমতা কত?",
        "mr": "तुमची दररोजची उत्पादन क्षमता किती आहे?",
        "gu": "તમારી દૈનિક ઉત્પાદન ક્ષમતા કેટલી છે?",
        "kn": "ನಿಮ್ಮ ದೈನಂದಿನ ಉತ್ಪಾದನಾ ಸಾಮರ್ಥ್ಯ ಎಷ್ಟು?",
        "ml": "നിങ്ങളുടെ പ്രതിദിന ഉൽപ്പാദന ശേഷി എത്രയാണ്?",
        "pa": "ਤੁਹਾਡੀ ਰੋਜ਼ਾਨਾ ਉਤਪਾਦਨ ਸਮਰੱਥਾ ਕੀ ਹੈ?",
    },
    "factory_area_size": {
        "hi": "Aapki factory ya karkhana kitne area mein faila hua hai?",
        "en": "What is the area size of your factory or workshop?",
        "ta": "உங்கள் குடோன் அல்லது தொழிற்சாலை எவ்வளவு பெரியது?",
        "te": "మీ ఫ్యాక్టరీ ఎంత విస్తీర్ణంలో ఉంది?",
        "bn": "আপনার কারখানা কত বড়?",
        "mr": "तुमचा कारखाना किती जागेत आहे?",
        "gu": "તમારું કારખાનું કેટલા વિસ્તારમાં છે?",
        "kn": "ನಿಮ್ಮ ಕಾರ್ಖಾನೆ ಎಷ್ಟು ದೊಡ್ಡದಾಗಿದೆ?",
        "ml": "നിങ്ങളുടെ ഫാക്ടറി എത്ര വലുതാണ്?",
        "pa": "ਤੁਹਾਡੀ ਫੈਕਟਰੀ ਕਿੰਨੀ ਵੱਡੀ ਹੈ?",
    },
    "major_machinery_used": {
        "hi": "Production ke liye kaun kaun si badi machines use karte hain?",
        "en": "What major machines or equipment do you use for production?",
        "ta": "உற்பத்திக்கு என்ன இயந்திரங்களை பயன்படுத்துகிறீர்கள்?",
        "te": "ఉత్పత్తి కోసం ఏ యంత్రాలను ఉపయోగిస్తారు?",
        "bn": "উত্পাদনের জন্য আপনি কোন মেশিন ব্যবহার করেন?",
        "mr": "उत्पादनासाठी तुम्ही कोणती यंत्रे वापरता?",
        "gu": "ઉત્પાદન માટે તમે કયા મશીનનો ઉપયોગ કરો છો?",
        "kn": "ಉತ್ಪಾದನೆಗಾಗಿ ನೀವು ಯಾವ ಯಂತ್ರಗಳನ್ನು ಬಳಸುತ್ತೀರಿ?",
        "ml": "ഉത്പാദനത്തിനായി നിങ്ങൾ ഏത് യന്ത്രങ്ങൾ ഉപയോഗിക്കുന്നു?",
        "pa": "ਤੁਸੀਂ ਉਤਪਾਦਨ ਲਈ ਕਿਹੜੀਆਂ ਮਸ਼ੀਨਾਂ ਦੀ ਵਰਤੋਂ ਕਰਦੇ ਹੋ?",
    },
}


def get_missing_critical_fields(
    extracted_entities: Dict,
) -> List[str]:
    """
    Identify which critical fields are still missing.

    The conversation only marks COMPLETE when ALL of these are filled.
    This ensures a natural 2-3 turn conversation that gathers enough
    data for a strong Gate 3 manufacturing confidence score.

    Returns:
        List of missing field names.
    """
    missing = []

    if not extracted_entities.get("enterprise_name"):
        missing.append("enterprise_name")

    if not extracted_entities.get("product_descriptions"):
        missing.append("product_descriptions")

    if not extracted_entities.get("manufacturing_process_keywords"):
        missing.append("manufacturing_process_keywords")

    if not extracted_entities.get("selling_channels") and not extracted_entities.get("buyer_types_mentioned"):
        missing.append("selling_channels")

    if not extracted_entities.get("buyer_geographies_mentioned"):
        missing.append("buyer_geographies_mentioned")

    if not extracted_entities.get("employees_count"):
        missing.append("employees_count")

    if not extracted_entities.get("years_in_business"):
        missing.append("years_in_business")

    if not extracted_entities.get("daily_production_capacity"):
        missing.append("daily_production_capacity")

    if not extracted_entities.get("factory_area_size"):
        missing.append("factory_area_size")

    if not extracted_entities.get("major_machinery_used"):
        missing.append("major_machinery_used")

    return missing


def get_followup_question(
    field: str, language: str = "hi"
) -> Optional[str]:
    """
    Get the follow-up question for a missing field in the given language.

    Args:
        field: Field name (e.g. 'product_descriptions').
        language: ISO language code.

    Returns:
        Question text in the requested language, or Hindi fallback.
    """
    questions = FOLLOWUP_QUESTIONS.get(field)
    if not questions:
        return None

    # Try exact language, then Hindi fallback, then English
    return questions.get(language, questions.get("hi", questions.get("en")))


def get_all_followup_questions(
    missing_fields: List[str], language: str = "hi"
) -> List[Dict[str, str]]:
    """
    Get follow-up questions for all missing fields.

    Returns:
        List of dicts with 'field' and 'question' keys.
    """
    questions = []
    for field in missing_fields:
        q = get_followup_question(field, language)
        if q:
            questions.append({"field": field, "question": q})
    return questions
