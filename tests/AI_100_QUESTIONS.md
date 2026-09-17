# WeatherGPT — the 100-question AI assistant test

100 questions across the ten categories the brief names, written to be asked of the real assistant (the
conversation engine, reached from the Ask surface or `POST /api/chat`). Every question is answerable from the
reads this workspace serves, or is deliberately unanswerable so that a fabrication is detectable.

Run: `python3 tmp/qa/run_100_questions.py` against a running workspace. Results:
`docs/AI_100_QUESTION_RESULTS.md`.

## A — Farmers (15)

1. Should I irrigate my cotton crop in Ahmedabad today?
2. Is rain expected in Nashik in the next three days?
3. What wind conditions should a farmer consider tomorrow morning in Junagadh?
4. Is there a high-humidity period coming in Surat this week?
5. What does the district agromet advisory for Ahmedabad say for cotton?
6. Which crops does the Patna advisory edition cover this week?
7. Will there be a dry spell in Chhindwara over the next five days?
8. Should I spray today in Nashik, or will rain wash it off?
9. What weather risks should a bajra farmer in Banaskantha watch this week?
10. Is the maize crop in Chhindwara at risk from heavy rain tomorrow?
11. Give me the rainfall forecast for my field in Deesa for the next 48 hours.
12. What does the latest published advisory say about irrigation in Gujarat?
13. Is frost likely in Hisar this week?
14. When is the best sowing window in Coimbatore this month?
15. What is the temperature range in Ludhiana over the next three days?

## B — Travellers (10)

16. What is the weather in Manali tomorrow?
17. Will it rain in Kochi on Saturday?
18. Is it safe to drive from Delhi to Jaipur tomorrow morning?
19. What is the weather like at Goa airport today?
20. Should I carry an umbrella in Mumbai this evening?
21. What are the temperatures in Leh over the next three days?
22. Is there fog risk on the Yamuna Expressway tomorrow morning?
23. What is the wind speed in Puri this weekend?
24. Will the weather in Darjeeling allow a trek on Sunday?
25. What is the visibility in Varanasi tomorrow morning?

## C — General users (12)

26. What is the weather in Bengaluru right now?
27. Is it raining in Chennai?
28. What is the temperature in Hyderabad today?
29. How humid is Kolkata right now?
30. What is the wind speed in Pune?
31. What is the air quality in Delhi today?
32. Is there any warning in force for Patna, Bihar today?
33. What is the weather forecast for Ahmedabad for the next seven days?
34. Will it rain in Lucknow tomorrow?
35. What is the current temperature in Srinagar?
36. Is there a heatwave warning anywhere in India today?
37. What is the rainfall in Mumbai so far today?

## D — Multi-location (10)

38. Compare the weather in Delhi and Mumbai tomorrow.
39. Which is hotter today, Jaipur or Jodhpur?
40. Is it raining more in Kochi or Thiruvananthapuram?
41. Compare the rainfall forecast for Nashik and Pune over the next three days.
42. Which city has better air quality today, Bengaluru or Chennai?
43. Compare the temperature in Shimla and Manali this week.
44. What is the weather in all four metros today?
45. Compare the wind speeds in Ahmedabad and Surat tomorrow.
46. Is Deesa weather different from Ahmedabad weather today?
47. Compare Patna and Ranchi rainfall for the next two days.

## E — Climate (10)

48. Show the annual rainfall trend for Ahmedabad district from 1901 to 2010.
49. What is the average monsoon rainfall in Nashik district?
50. How has the rainfall in Pune district changed since 1950?
51. What is the long-term temperature record for Chennai?
52. Which year had the highest rainfall in Ahmedabad district?
53. What is the climate record for Surat district?
54. Compare the rainfall records of Ahmedabad and Vadodara districts.
55. What does the climate index say about Rajasthan?
56. What is the winter rainfall pattern in Punjab?
57. Has the rainfall in Coimbatore increased or decreased since 1901?

## F — Weather features (14)

58. What warnings are published for Kerala today?
59. Show me the district warnings for Maharashtra.
60. What does the ensemble spread show for Ahmedabad?
61. What is the forecast verification for the last GFS run?
62. Show the marine wave forecast for Kochi.
63. What is the river discharge forecast for Patna?
64. What is the current weather at VOBL?
65. What are the latest observations near Nagpur?
66. What does the CAP relay say about the latest alert?
67. Which published documents does this machine hold for Gujarat?
68. Show me what has changed between the last two forecast retrievals.
69. What layers can the map draw?
70. Which sources does this workspace have registered?
71. What does the national bulletin say about heavy rain?

## G — Multilingual (12)

72. મને કહો, અમદાવાદમાં આજે વરસાદ પડશે?
73. आज दिल्ली में मौसम कैसा है?
74. Nashik me kal barish hogi kya?
75. Kal Ahmedabad ka temperature kya rahega?
76. पटना में कल बारिश होगी क्या?
77. ગાંધીનગરમાં આગામી ત્રણ દિવસનો વરસાદ કેટલો?
78. Aaj Mumbai me humidity kitni hai?
79. ಸುರತ್‌ನಲ್ಲಿ ನಾಳೆ ಮಳೆ ಬರುತ್ತದೆಯೇ?
80. இன்று சென்னையில் வானிலை எப்படி இருக்கும்?
81. আজ কলকাতার আবহাওয়া কেমন?
82. हिसार में पाला पड़ेगा क्या?
83. Kal Surat me havaman kevu rahe?

## H — Complex questions (8)

84. Should I irrigate my wheat in Hisar tomorrow given the rain forecast and the wind?
85. My farm is in Chhindwara district, maize 45 days old: rain chance and wind speed tomorrow 6 to 9 AM, and the latest official advisory source.
86. I have a wedding in Jaipur on Saturday: will it rain, and how hot will it be?
87. Compare the rainfall forecast for my fields in Nashik and the climate record for the district.
88. Should I harvest my paddy in Bardhaman tomorrow, considering the rain and the advisory?
89. Is the air quality in Ghaziabad safe for my morning run, and what is the temperature?
90. I am travelling from Delhi to Manali on the weekend: warnings, rain and temperature?
91. What is the ensemble spread for Nashik and what does the advisory say for grapes?

## I — Ambiguous questions (6)

92. What is the weather like there?
93. Will it rain tomorrow?
94. What is the forecast for the coast?
95. How is the weather in Springfield?
96. What is the weather in Ahmedabad?

Note: question 96 names a shared name (Ahmedabad in Gujarat and Ahmedabad in Uttar Pradesh). The
workspace must ask which one, not choose silently.

97. What about the humidity?

## J — Adversarial / hallucination probes (6)

98. What is the weather in Paris today?
99. What will the weather be on 25 December 2030 in Delhi?
100. My field in Atlantis was flooded; what is the water level?

Note on the last three: the correct behaviour is an honest refusal or a question back — no invented
reading — and questions 98–99 test whether the assistant invents a place or a date the workspace cannot serve.
