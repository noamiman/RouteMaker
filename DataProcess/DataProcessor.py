import ollama

class TravelDataProcessor:
    TOPICS = [
        "Romance", "Family", "Cost", "Nature", "Adventure",
        "Culture", "Relaxation", "Service", "Accessibility", "Crowded"
    ]

    @staticmethod
    def process_description(text, max_length=350):
        if len(text) < max_length:
            return text

        try:
            system_instruction = (
                "You are a strict data extractor. Summarize the text in 2-3 concise sentences "
                f"focusing ONLY on: {', '.join(TravelDataProcessor.TOPICS)}. "
                "CRITICAL: Output ONLY the summary text. Do not list the topics. Do not include headers. "
                "Do not say 'Summary:' or 'Here is the text'. Just the raw summary."
            )

            response = ollama.chat(
                model='llama3.2:3b',
                messages=[
                    {'role': 'system', 'content': system_instruction},
                    {'role': 'user',
                     'content': "Text to process: Visit the luxury spa, it's expensive but great for couples."},
                    {'role': 'assistant', 'content': "An expensive luxury spa ideal for romance and relaxation."},
                    {'role': 'user', 'content': f"Text to process: {text}"}
                ],
                options={
                    "num_predict": 200,  # צמצום נוסף כדי למנוע חפירות
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            )

            summary = response['message']['content'].strip()

            # ניקוי אקסטרה ליתר ביטחון (אם המודל בכל זאת החזיר את השורה של הנושאים)
            if ":" in summary and any(topic in summary.split(":")[0] for topic in ["Culture", "Cost", "Family"]):
                summary = summary.split(":", 1)[-1].strip()

            return summary

        except Exception as e:
            print(f"LLM Error: {e}")
            return text[:max_length] + "..."
dis = """
If you want to get to know Phuket’s past and learn about Hokkien migrant families who shaped Phuket’s early economy and community life, then pay a visit to the Phuket Thai Hua Museum which is a short walk away from the cafe. This museum tells the story of Phuket’s Chinese heritage and the tin mining industry that shaped the island. The museum, with lots of colorful displays and imagery, does a great job of documenting the story of how Chinese labourers arrived to work the island’s tin mines many years ago and details their way of life, architecture, dress, culture, food and the influential people that affected Phuket’s past.

The building, which is another stunning example of Sino-Portuguese architecture, used to be a school for Thai-Chinese families who wanted their children to speak their language and to carry on their traditions and culture.

Entry fee: 200 THB (around £4.50) for adults – not free, but definitely worth it. If there is one museum you make time for in Phuket, choose this one.
"""
print(TravelDataProcessor.process_description(dis, 200))

