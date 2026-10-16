"""Practical adult technology education, English source editions awaiting local-language review.

Skills are grouped for adults and beginners, not by a school grade.
Exercises use fictional or non-sensitive personal information wherever possible.
"""
ADULT_LEVEL = "Adult Education"
ADULT_LESSONS = [
  {
    "slug": "smartphone-basics",
    "title": "Understand your smartphone",
    "subject": "Digital Foundations",
    "level": "Adult Education",
    "concept": "Smartphone navigation",
    "explanation": "A smartphone can make calls, send messages, take photos and use applications. The home screen contains app icons, and Settings controls features such as sound and display.",
    "steps": [
      "Unlock your phone using a method you can remember.",
      "Identify the Home, Back and Settings controls.",
      "Increase text size if small letters are difficult to read."
    ],
    "task": "Open Settings and locate the display or text-size option.",
    "question": "What do you use to change the phone's text size?",
    "options": [
      "Settings",
      "A SIM-card tray",
      "A phone case"
    ],
    "answer": 0
  },
  {
    "slug": "mobile-data-wifi",
    "title": "Connect safely to the internet",
    "subject": "Digital Foundations",
    "level": "Adult Education",
    "concept": "Mobile data and Wi-Fi",
    "explanation": "Mobile data uses your network provider's connection and may consume a paid data bundle. Wi-Fi connects through a wireless network. Both allow you to browse websites and use online apps.",
    "steps": [
      "Look for the Wi-Fi and mobile-data icons.",
      "Connect only to a network you trust.",
      "Check the remaining data balance using your provider's official method."
    ],
    "task": "Find the phone option that shows whether you are connected through Wi-Fi or mobile data.",
    "question": "Which connection commonly uses a mobile network data bundle?",
    "options": [
      "Bluetooth only",
      "Mobile data",
      "Airplane mode"
    ],
    "answer": 1
  },
  {
    "slug": "typing-and-voice",
    "title": "Type messages and use voice input",
    "subject": "Digital Foundations",
    "level": "Adult Education",
    "concept": "Text and voice input",
    "explanation": "A phone keyboard lets you type messages and search. Some devices also support dictation using a microphone. Always check dictated text before you send it.",
    "steps": [
      "Open a notes application.",
      "Type a short message and correct one word.",
      "If voice typing is available, dictate a sentence and check it before saving."
    ],
    "task": "Write a short shopping list in a notes app.",
    "question": "What should you do before sending a voice-typed message?",
    "options": [
      "Ignore the content",
      "Share it widely",
      "Read and correct the words"
    ],
    "answer": 2
  },
  {
    "slug": "photos-files",
    "title": "Find and share photos and files",
    "subject": "Digital Foundations",
    "level": "Adult Education",
    "concept": "Files and photo management",
    "explanation": "Photos are usually stored in a gallery or photos app. Downloads and documents may appear in Files. Share only the files you intend to share and check the recipient.",
    "steps": [
      "Take a photograph of a non-sensitive object.",
      "Find it in Photos or Gallery.",
      "Practice sharing it with someone you trust, or cancel before sending."
    ],
    "task": "Find your Downloads folder and identify one harmless file.",
    "question": "What should you check before sharing a file?",
    "options": [
      "The file and recipient",
      "Only the screen brightness",
      "Whether the phone is charging"
    ],
    "answer": 0
  },
  {
    "slug": "email-basics",
    "title": "Use email for work and learning",
    "subject": "Online Safety & Services",
    "level": "Adult Education",
    "concept": "Email",
    "explanation": "Email allows people to send written messages and attachments. A subject line explains the topic. Carefully check recipient addresses and attachments before sending.",
    "steps": [
      "Open your existing email app or visit your provider's official website.",
      "Draft a message with a meaningful subject.",
      "Check the recipient, then send to someone you trust or keep it as a draft."
    ],
    "task": "Draft a short professional email asking for information.",
    "question": "What does an email subject line usually describe?",
    "options": [
      "Your screen size",
      "What the message is about",
      "Your phone battery"
    ],
    "answer": 1
  },
  {
    "slug": "recognize-scams",
    "title": "Recognize scams, fake links and OTP requests",
    "subject": "Online Safety & Services",
    "level": "Adult Education",
    "concept": "Phishing and account security",
    "explanation": "Criminals can impersonate banks, delivery companies or friends. Be cautious of urgent messages that demand money, passwords or one-time passwords (OTPs). Never share an OTP with another person.",
    "steps": [
      "Read a sample suspicious message without opening its link.",
      "Look for pressure, fake websites or requests for secrets.",
      "Use an official app or trusted contact number to verify a claim."
    ],
    "task": "Write down two signs that a message may be fraudulent.",
    "question": "What should you do when someone asks for your one-time password?",
    "options": [
      "Share it only with a caller",
      "Post it in a group chat",
      "Keep it private and verify through official channels"
    ],
    "answer": 2
  },
  {
    "slug": "search-trust",
    "title": "Search the web and check information",
    "subject": "Online Safety & Services",
    "level": "Adult Education",
    "concept": "Online research and verification",
    "explanation": "A search engine helps you find websites, but not every result is correct. Compare reliable sources and check dates before acting on health, finance or public-service information.",
    "steps": [
      "Search for a simple how-to topic.",
      "Compare two sources and their publication dates.",
      "Look for the official agency or business website when relevant."
    ],
    "task": "Find instructions for changing text size on your phone from a reliable source.",
    "question": "Which is the safer way to evaluate a surprising online claim?",
    "options": [
      "Compare credible sources",
      "Trust the first result automatically",
      "Forward it before checking"
    ],
    "answer": 0
  },
  {
    "slug": "digital-payments",
    "title": "Understand digital payments safely",
    "subject": "Online Safety & Services",
    "level": "Adult Education",
    "concept": "Digital payment safety",
    "explanation": "Digital payments can transfer money between accounts. Before confirming a payment, check the recipient and amount. Do not disclose your PIN or OTP to anyone, including people claiming to be support staff.",
    "steps": [
      "Open your payment app without making a transfer.",
      "Find where recipient details and the amount would be confirmed.",
      "Practice identifying account alerts and the official support channel."
    ],
    "task": "List three checks to make before confirming a transfer; do not send money during this exercise.",
    "question": "What should you confirm before making a transfer?",
    "options": [
      "The recipient and amount",
      "The weather forecast",
      "Your photo gallery"
    ],
    "answer": 0
  },
  {
    "slug": "documents-cv",
    "title": "Create a simple document or CV",
    "subject": "Work, Business & AI",
    "level": "Adult Education",
    "concept": "Digital documents",
    "explanation": "A document editor allows you to write, correct and format letters, CVs and reports. Clear headings and concise sentences make documents easier to read.",
    "steps": [
      "Open a word-processing app or an offline document editor.",
      "Create a page with your name, skills and one experience example.",
      "Save a copy without sharing private details publicly."
    ],
    "task": "Create a simple practice CV using fictional contact information.",
    "question": "Which tool is most suitable for writing a CV?",
    "options": [
      "A calculator",
      "A document editor",
      "A flashlight"
    ],
    "answer": 1
  },
  {
    "slug": "spreadsheets-budget",
    "title": "Use a spreadsheet for simple budgeting",
    "subject": "Work, Business & AI",
    "level": "Adult Education",
    "concept": "Spreadsheets",
    "explanation": "Spreadsheets organize numbers into rows and columns. Formulas can calculate totals. A simple income-and-expense sheet can help you understand your finances.",
    "steps": [
      "Open a spreadsheet or draw a table on paper.",
      "Enter three fictional income and expense amounts.",
      "Add up the amounts, then compare the totals."
    ],
    "task": "Make a sample weekly budget with fictional figures.",
    "question": "Which feature helps calculate totals in a spreadsheet?",
    "options": [
      "A formula",
      "A wallpaper",
      "A camera filter"
    ],
    "answer": 0
  },
  {
    "slug": "sell-online",
    "title": "Introduce a small business online",
    "subject": "Work, Business & AI",
    "level": "Adult Education",
    "concept": "Digital business",
    "explanation": "A small business can share product details online. Clear descriptions, accurate prices and respectful customer service help buyers understand an offer. Avoid posting private customer details publicly.",
    "steps": [
      "Write a description of one product or service.",
      "Choose a realistic fictional price and a safe contact method.",
      "Review the draft for clarity and remove personal or misleading claims."
    ],
    "task": "Create a sample product listing without publishing it.",
    "question": "Which is most helpful in an online product listing?",
    "options": [
      "A misleading promise",
      "A clear description and accurate price",
      "A customer's private information"
    ],
    "answer": 1
  },
  {
    "slug": "ai-assistants",
    "title": "Use AI assistants thoughtfully",
    "subject": "Work, Business & AI",
    "level": "Adult Education",
    "concept": "Generative AI literacy",
    "explanation": "An AI assistant can help draft text, explain concepts and suggest ideas. AI can make mistakes or invent facts, so verify important answers and never paste passwords, private documents or sensitive data.",
    "steps": [
      "Write a harmless request asking AI to explain a phone setting.",
      "Ask for a simpler step-by-step explanation.",
      "Compare the response with a trusted source and correct any mistakes."
    ],
    "task": "Draft one prompt asking for help with a basic workplace task using fictional information.",
    "question": "What should you do with an important answer from an AI assistant?",
    "options": [
      "Trust it without checking",
      "Send your password for better results",
      "Verify it using reliable sources"
    ],
    "answer": 2
  }
]
