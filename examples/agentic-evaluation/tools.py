WEATHER_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for general information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
]

TRAVEL_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two cities on a given date",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "Departure city"},
                    "to_city": {"type": "string", "description": "Destination city"},
                    "date": {
                        "type": "string",
                        "description": "Travel date (YYYY-MM-DD)",
                    },
                },
                "required": ["from_city", "to_city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_alternative_routes",
            "description": "Search for alternative flight routes or connection options between two cities on a given date",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "Departure city"},
                    "to_city": {"type": "string", "description": "Destination city"},
                    "date": {
                        "type": "string",
                        "description": "Travel date (YYYY-MM-DD)",
                    },
                },
                "required": ["from_city", "to_city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_details",
            "description": "Get detailed information about a specific flight by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "Flight ID"},
                },
                "required": ["flight_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Book a specific flight by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "Flight ID to book"},
                },
                "required": ["flight_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_book",
            "description": "Search for available flights, return full flight details (airline, price, departure and arrival times), and book the best option — all in one step",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "Departure city"},
                    "to_city": {"type": "string", "description": "Destination city"},
                    "date": {
                        "type": "string",
                        "description": "Travel date (YYYY-MM-DD)",
                    },
                },
                "required": ["from_city", "to_city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_booking",
            "description": "Verify that a booking was successfully completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID to verify",
                    },
                },
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an existing flight booking",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID to cancel",
                    },
                },
                "required": ["booking_id"],
            },
        },
    },
]

SUPPORT_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_account",
            "description": "Look up a customer's account details by user ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Customer user ID"},
                },
                "required": ["user_id"],
            },
        },
    },
]
