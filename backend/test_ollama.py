import ollama

print("Before request")

response = ollama.chat(
    model="llama3.2",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)

print("After request")
print(response)