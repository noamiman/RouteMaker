# import pandas as pd
# with open ("../DataProcess/Unified_Countries/Thailand_processed", "r") as f:
#     df = pd.read_csv(f)[0:5]
#
# # הצגת כל השורות
# pd.set_option('display.max_rows', None)
#
# # הצגת כל העמודות
# pd.set_option('display.max_columns', None)
#
# # מניעת קיצור טקסט ארוך בתוך התאים (חשוב לתיאורים)
# pd.set_option('display.max_colwidth', None)
#
# # הצגת רוחב כולל של הטבלה בלי "לשבור" שורות
# pd.set_option('display.width', None)
# import pandas as pd
# import ollama
#
#
# def summarize_with_llama(descriptions):
#     """
#     שולח רשימת תיאורים ל-Llama 3.2 ומחזיר סיכום מאוחד.
#     """
#     # איחוד כל התיאורים לטקסט אחד עם מספור
#     combined_text = "\n".join([f"- {desc}" for desc in descriptions])
#
#     prompt = f"""
#     Combine these descriptions into one professional paragraph of about 50 words.
#     Return ONLY the summary text, without any introductory phrases like "Here is the summary" or "I'd be happy to help".
#
#     Descriptions:
#     {combined_text}
#     """
#
#     try:
#         response = ollama.chat(model='llama3.2:3b', messages=[
#             {
#                 'role': 'user',
#                 'content': prompt,
#             },
#         ])
#         return response['message']['content'].strip()
#     except Exception as e:
#         return f"Error during summarization: {e}"
#
#
# # 1. טעינת הנתונים (נניח שהטבלה שלך ב-df)
# # df = pd.read_csv('your_data.csv')
#
# # 2. ביצוע אגרגציה ראשונית
# # אנחנו ממצעים מספרים ואוספים טקסט לרשימה
# agg_rules = {
#     'country': 'first',
#     'google_maps_url': 'first',
#     'description': lambda x: list(set(x)),  # לוקח רק תיאורים ייחודיים לרשימה
#     'romance': 'mean',
#     'family': 'mean',
#     'cost': 'mean',
#     'nature': 'mean',
#     'adventure': 'mean',
#     'culture': 'mean',
#     'food': 'mean',
#     'relaxation': 'mean',
#     'service': 'mean',
#     'accessibility': 'mean'
# }
#
# print("Grouping and calculating averages...")
# df_grouped = df.groupby('place', as_index=False).agg(agg_rules)
#
# # 3. הרצת הסיכום של Llama על כל קבוצה
# print("Summarizing descriptions with Llama 3.2 (this may take a moment)...")
# df_grouped['description'] = df_grouped['description'].apply(summarize_with_llama)
#
# # 4. עיגול הממוצעים לנוחות (אופציונלי)
# numeric_cols = df_grouped.select_dtypes(include=['number']).columns
# df_grouped[numeric_cols] = df_grouped[numeric_cols].round(1)
#
# # הצגת התוצאה
# print("\nProcess Complete! Final Table:")
# print(df_grouped)
#
# # שמירה לקובץ חדש
# # df_grouped.to_csv('final_places_summary.csv', index=False)

# ---

