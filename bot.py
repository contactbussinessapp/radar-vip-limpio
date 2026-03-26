import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
import os

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1zGZF5meVfgRZvRLSvKGelwYs2h3pgA7YEpC_1xj9cTk/export?format=csv"
user_state = {}

def get_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df.fillna('', inplace=True)
        return df
    except Exception as e:
        print(f"Error leyendo el Sheet: {e}")
        return pd.DataFrame()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🇦🇷 Argentina", callback_data="loc_AR"),
        InlineKeyboardButton("🇨🇱 Chile", callback_data="loc_CL"),
        InlineKeyboardButton("🇺🇾 Uruguay", callback_data="loc_UY"),
        InlineKeyboardButton("🌍 Resto de Latam/USA/Global", callback_data="loc_GLOBAL")
    )
    bot.send_message(message.chat.id, "¡Hola! Bienvenido a Radar VIP. 🚀\nPor favor, selecciona tu país/región:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('loc_'))
def handle_location(call):
    loc = call.data.split('_')[1]
    user_state[call.message.chat.id] = loc
    df = get_data()
    
    if df.empty:
        bot.send_message(call.message.chat.id, "Error de conexión con la base de datos.")
        return

    df_ar = df[df['Pais (ISO)'] == 'AR']
    df_cl = df[df['Pais (ISO)'] == 'CL']
    df_uy = df[df['Pais (ISO)'] == 'UY']
    df_global = df[df['Pais (ISO)'].isin(['AM-INT', 'GLOBAL'])]
    
    bot.answer_callback_query(call.id)
    
    if loc == 'AR':
        oportunidades = df_ar.head(7)
        resp = "🇦🇷 **Oportunidades del Día** 🇦🇷\n\n"
        for _, row in oportunidades.iterrows():
            resp += f"🔹 [{row['Producto o Sección']}]({row['Link']})\n"
        resp += "\n¿Qué estás buscando hoy?"
    elif loc == 'CL':
        scope = pd.concat([df_cl, df_global])
        random_items = scope.sample(n=min(5, len(scope)))
        resp = "🇨🇱 **Te podría interesar** 🇨🇱\n\n"
        for _, row in random_items.iterrows():
            resp += f"🔹 [{row['Producto o Sección']}]({row['Link']})\n"
        resp += "\n¿Qué estás buscando?"
    elif loc == 'UY':
        scope = pd.concat([df_uy, df_global])
        random_items = scope.sample(n=min(3, len(scope)))
        resp = "🇺🇾 **Productos Destacados** 🇺🇾\n\n"
        for _, row in random_items.iterrows():
            resp += f"🔹 [{row['Producto o Sección']}]({row['Link']})\n"
        resp += "\n¿Qué andás buscando, bo?"
    elif loc == 'GLOBAL':
        scope = df_global
        random_items = scope.sample(n=min(3, len(scope)))
        resp = "🌍 **Mejores Opciones** 🌍\n\n"
        for _, row in random_items.iterrows():
            resp += f"🔹 [{row['Producto o Sección']}]({row['Link']})\n"
        resp += "\n¿Qué buscas?"

    bot.send_message(call.message.chat.id, resp, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda message: True)
def handle_search(message):
    chat_id = message.chat.id
    if chat_id not in user_state:
        send_welcome(message)
        return
        
    loc = user_state[chat_id]
    query = message.text.lower()
    df = get_data()
    
    df_ar = df[df['Pais (ISO)'] == 'AR']
    df_cl = df[df['Pais (ISO)'] == 'CL']
    df_uy = df[df['Pais (ISO)'] == 'UY']
    df_global = df[df['Pais (ISO)'].isin(['AM-INT', 'GLOBAL'])]
    
    if loc == 'AR':
        scope = pd.concat([df_ar, df_global])
    elif loc == 'CL':
        scope = pd.concat([df_cl, df_global])
    elif loc == 'UY':
        scope = pd.concat([df_uy, df_global])
    else:
        scope = df_global

    def match_score(row):
        keywords_str = str(row['Keywords'])
        keywords = [k.strip().lower() for k in keywords_str.split(',')]
        query_words = query.split()
        return sum(1 for q in query_words if any(q in k for k in keywords))

    scope['score'] = scope.apply(match_score, axis=1)
    matches = scope[scope['score'] > 0].sort_values(by='score', ascending=False)
    
    if matches.empty:
        bot.send_message(chat_id, "No encontré resultados exactos. Intenta con otras palabras.")
        return
        
    top_matches = matches.head(5)
    resp = "🔍 **Aquí tienes los resultados:**\n\n"
    for _, row in top_matches.iterrows():
        resp += f"✅ [{row['Producto o Sección']}]({row['Link']})\n"
        
    bot.send_message(chat_id, resp, parse_mode='Markdown', disable_web_page_preview=True)

if __name__ == "__main__":
    print("Iniciando Radar VIP en Background Worker...")
    bot.infinity_polling(skip_pending=True)
