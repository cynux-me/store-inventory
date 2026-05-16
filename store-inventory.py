import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# --- হেল্পার ফাংশন ---
def bn_to_en(number_str):
    if not number_str: return ""
    bn_digits = '০১২৩৪৫৬৭৮৯'
    en_digits = '0123456789'
    conv = str.maketrans(bn_digits, en_digits)
    return str(number_str).translate(conv)

def init_db():
    conn = sqlite3.connect('ts_hardware_ultimate.db')
    cursor = conn.cursor()
    
    # products টেবিল সংশোধন: নাম এবং কোম্পানিকে একত্রে UNIQUE করা হয়েছে
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY, 
                       name TEXT, 
                       company TEXT, 
                       unit TEXT, 
                       cost_price REAL, 
                       stock REAL,
                       UNIQUE(name, company))''') # এই লাইনটি যোগ করা হয়েছে
                       
    cursor.execute('''CREATE TABLE IF NOT EXISTS ledger 
                      (id INTEGER PRIMARY KEY, 
                       date TEXT, 
                       item_name TEXT, 
                       company TEXT, 
                       customer TEXT, 
                       type TEXT, 
                       qty REAL, 
                       rate REAL, 
                       total REAL, 
                       cash_paid REAL)''')

    conn.commit()
    conn.close()

class HardwareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("তৈয়্যবিয়া স্টোর ২০১৬")
        
        # আইকন না থাকলে যাতে এরর না দেয় তার জন্য ট্রাই-এক্সেপ্ট
        try:
            self.root.iconbitmap("mylogo.ico")
        except:
            pass
            
        self.root.geometry("1400x850")
        self.root.configure(bg="#f0f2f5")

        # ১. আগে ইন্টারফেসের মেইন টাইটেল এবং ট্যাব সেটআপ করুন
        tk.Label(self.root, text="🛒 তৈয়্যবিয়া স্টোর ইনভেন্টরি ও স্মার্ট রিপোর্ট সিস্টেম", 
                 font=("Arial", 20, "bold"), bg="#2c3e50", fg="white", pady=15).pack(fill="x")

        self.tabs = ttk.Notebook(self.root)
        self.t1 = tk.Frame(self.tabs, bg="#f0f2f5")
        self.t2 = tk.Frame(self.tabs, bg="#f0f2f5")
        self.t3 = tk.Frame(self.tabs, bg="#f0f2f5")
        
        self.tabs.add(self.t1, text=" স্টক ও বেচাকেনা ")
        self.tabs.add(self.t2, text=" বিস্তারিত রিপোর্ট ও এক্সপোর্ট ")
        self.tabs.add(self.t3, text=" কাস্টমার পেমেন্ট ও বকেয়া ")
        self.tabs.pack(expand=1, fill="both", padx=10, pady=10)

        # ২. সব ট্যাব এবং ডাটা লোড ফাংশন কল করা
        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()
        self.refresh_data()

    # ইউনিট কনভার্সন ফাংশন (অবশ্যই self প্যারামিটার সহ)
    def convert_to_base_unit(self, qty, unit):
        try:
            qty = float(qty)
            unit = str(unit).strip().lower()
            if unit in ['dozen', 'ডজন']:
                return qty * 12
            elif unit in ['foot', 'ফুট', 'feet']:
                return qty * 12  # ১ ফুট = ১২ ইঞ্চি
            elif unit in ['gaj', 'গজ', 'yard']:
                return qty * 36  # ১ গজ = ৩৬ ইঞ্চি
            elif unit in ['meter', 'মিটার']:
                return qty * 100 # ১ মিটার = ১০০ সেমি
            return qty
        except:
            return qty

    def filter_stock_by_keyword(self, event=None):
        """কি-ওয়ার্ড দিয়ে স্টক টেবিল ফিল্টার করা"""
        keyword = self.ent_search_stock.get().strip() # সার্চ বক্সের নাম
        for row in self.tree_stock.get_children():
            self.tree_stock.delete(row)
            
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        
        # কি-ওয়ার্ড দিয়ে নাম বা কোম্পানির মধ্যে খোঁজা
        query = "SELECT * FROM products WHERE name LIKE ? OR company LIKE ?"
        cursor.execute(query, (f'%{keyword}%', f'%{keyword}%'))
        
        for r in cursor.fetchall():
            self.tree_stock.insert("", "end", values=r)
        conn.close()

    def setup_tab1(self):
        """ট্যাব ১: ইনভেন্টরি এন্ট্রি এবং স্টক ম্যানেজমেন্ট (সব ফিচারসহ সংশোধিত)"""
        
        # --- মেইন লেআউট ফ্রেম ---
        f_left = tk.Frame(self.t1, bg="#f0f2f5")
        f_left.pack(side="left", fill="y", padx=20, pady=10)

        f_right = tk.Frame(self.t1, bg="white")
        f_right.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        # ---------------------------------------------------------
        # ১. নতুন স্টক যোগ (Purchase Section)
        # ---------------------------------------------------------
        f_buy = tk.LabelFrame(f_left, text=" ১. নতুন স্টক যোগ ", font=("Arial", 11, "bold"), 
                              padx=15, pady=10, bg="white", fg="#2980b9")
        f_buy.pack(fill="x", pady=5)
        
        self.entries_buy = {}

        # তারিখ এন্ট্রি
        tk.Label(f_buy, text="তারিখ (YYYY-MM-DD):", bg="white").grid(row=0, column=0, sticky="w")
        ent_date = tk.Entry(f_buy)
        ent_date.grid(row=0, column=1, pady=2)
        ent_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entries_buy['date'] = ent_date

        # সাজেশন লিস্টবক্স তৈরি (আগের মতোই আছে)
        self.name_listbox = tk.Listbox(self.t1, height=5, exportselection=0)
        self.comp_listbox = tk.Listbox(self.t1, height=5, exportselection=0)
        self.cust_listbox = tk.Listbox(self.t2, height=5, exportselection=0) 

        # পণ্যের নাম ও সাজেশন
        tk.Label(f_buy, text="পণ্যের নাম:", bg="white").grid(row=1, column=0, sticky="w")
        self.entries_buy['name'] = tk.Entry(f_buy, width=20)
        self.entries_buy['name'].grid(row=1, column=1, pady=2)
        
        # কোম্পানি ও সাজেশন
        tk.Label(f_buy, text="কোম্পানি:", bg="white").grid(row=2, column=0, sticky="w")
        self.entries_buy['comp'] = tk.Entry(f_buy, width=20)
        self.entries_buy['comp'].grid(row=2, column=1, pady=2)

        # --- নতুন বাইন্ডিং যোগ করা হয়েছে (সাজেশন গায়েব করার জন্য) ---
        self.entries_buy['name'].bind('<KeyRelease>', lambda e: self.show_suggestions(e, 'name'))
        self.entries_buy['comp'].bind('<KeyRelease>', lambda e: self.show_suggestions(e, 'company'))

        # এখানে 'after' ব্যবহার করা হয়েছে যাতে মাউস ক্লিক করার সময়টুকু পাওয়া যায়
        self.entries_buy['name'].bind('<FocusOut>', lambda e: self.t1.after(200, self.name_listbox.place_forget))
        self.entries_buy['comp'].bind('<FocusOut>', lambda e: self.t1.after(200, self.comp_listbox.place_forget))

        # কেনা দাম ও পরিমাণ
        tk.Label(f_buy, text="কেনা দাম:", bg="white").grid(row=3, column=0, sticky="w")
        self.entries_buy['price'] = tk.Entry(f_buy)
        self.entries_buy['price'].grid(row=3, column=1, pady=2)

        tk.Label(f_buy, text="পরিমাণ:", bg="white").grid(row=4, column=0, sticky="w")
        self.entries_buy['qty'] = tk.Entry(f_buy)
        self.entries_buy['qty'].grid(row=4, column=1, pady=2)
        
        # একক (Unit)
        tk.Label(f_buy, text="একক:", bg="white").grid(row=5, column=0, sticky="w")
        unit_list = ["Pcs", "Bag", "Kg", "Ltr", "Dozen", "Foot", "Gaj", "Inch", "Meter", "CM", "MM"]
        self.combo_unit = ttk.Combobox(f_buy, values=unit_list, width=17)
        self.combo_unit.grid(row=5, column=1, pady=2)
        self.combo_unit.current(0)
        
        # সেভ বাটন
        tk.Button(f_buy, text="📥 স্টক সেভ করুন", bg="#3498db", fg="white", font=("Arial", 10, "bold"), 
                  command=self.add_product).grid(row=6, columnspan=2, pady=10, sticky="ew")

        # ---------------------------------------------------------
        # ২. পণ্য বিক্রি ফর্ম (Sale Section - আগের ফিচার সব আছে)
        # ---------------------------------------------------------
        f_sale = tk.LabelFrame(f_left, text=" ২. মাল বিক্রি ও অ্যাকশন ", font=("Arial", 11, "bold"), 
                               padx=15, pady=10, bg="white", fg="#e67e22")
        f_sale.pack(fill="x", pady=5)
        
        sale_labels = ["তারিখ:", "কাস্টমার নাম:", "আইটেম বাছুন:", "পরিমাণ:", "বিক্রয় একক:", "বিক্রয় মূল্য:", "নগদ জমা:"]
        for i, txt in enumerate(sale_labels): 
            tk.Label(f_sale, text=txt, bg="white").grid(row=i, column=0, sticky="w")
        
        self.ent_sale_date = tk.Entry(f_sale)
        self.ent_sale_date.grid(row=0, column=1, pady=2)
        self.ent_sale_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.ent_cust_name = tk.Entry(f_sale)
        self.ent_cust_name.grid(row=1, column=1, pady=2)
        
        self.combo_sell_item = ttk.Combobox(f_sale, width=17)
        self.combo_sell_item.grid(row=2, column=1, pady=2)
        self.combo_sell_item.bind("<KeyRelease>", self.filter_item_dropdown)
        
        self.ent_sell_qty = tk.Entry(f_sale)
        self.ent_sell_qty.grid(row=3, column=1, pady=2)

        self.combo_sell_unit = ttk.Combobox(f_sale, values=["Pcs", "Inch", "Foot", "Gaj", "Dozen", "Meter", "Kg", "Ltr"], width=17)
        self.combo_sell_unit.grid(row=4, column=1, pady=2)
        self.combo_sell_unit.current(0)
        
        self.ent_sell_price = tk.Entry(f_sale)
        self.ent_sell_price.grid(row=5, column=1, pady=2)
        
        self.ent_sell_cash = tk.Entry(f_sale)
        self.ent_sell_cash.grid(row=6, column=1, pady=2)

        # অ্যাকশন বাটনসমূহ
        tk.Button(f_sale, text="✅ বিক্রি সম্পন্ন", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), 
                  command=self.make_sale).grid(row=7, columnspan=2, pady=10, sticky="ew")
        
        tk.Button(f_sale, text="🗑️ পণ্য ডিলিট", bg="#e74c3c", fg="white", 
                  command=self.delete_selected_stock).grid(row=8, columnspan=2, pady=5, sticky="ew")
        
        tk.Button(f_sale, text="🖨️ পুরোনো মেমো প্রিন্ট (ID দিয়ে)", bg="#34495e", fg="white", 
                  command=self.generate_invoice_by_id).grid(row=9, columnspan=2, pady=5, sticky="ew")

        # ---------------------------------------------------------
        # ৩. ডান পাশ: স্মার্ট ফিল্টার বার (সব আগের মতোই আছে)
        # ---------------------------------------------------------
        f_filter = tk.Frame(f_right, bg="white")
        f_filter.pack(fill="x", pady=5)
        
        tk.Label(f_filter, text="🔍 পণ্য খুঁজুন:", bg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        self.ent_search_stock = tk.Entry(f_filter, width=30, font=("Arial", 10))
        self.ent_search_stock.pack(side="left", padx=5)
        self.ent_search_stock.bind("<KeyRelease>", self.filter_stock_by_keyword)
        
        tk.Button(f_filter, text="সব দেখুন", bg="#ecf0f1", command=self.refresh_data).pack(side="left", padx=5)

        self.combo_search_item = ttk.Combobox(f_filter) 

        self.lbl_stock_summary = tk.Label(f_right, text="স্টক চেক করুন...", font=("Arial", 11, "bold"), 
                                          bg="#ecf0f1", pady=5)
        self.lbl_stock_summary.pack(fill="x")

        # টেবিল (Treeview)
        self.tree_stock = ttk.Treeview(f_right, columns=("ID", "N", "C", "U", "S", "P"), show='headings')
        for col, txt in zip(self.tree_stock["columns"], ["ID", "নাম", "কোম্পানি", "একক", "স্টক", "কেনা দাম"]):
            self.tree_stock.heading(col, text=txt)
            self.tree_stock.column(col, width=100, anchor="center")
        
        self.tree_stock.pack(expand=True, fill="both")
        self.tree_stock.bind("<Double-1>", self.open_history_popup)
        self.tree_stock.bind("<Delete>", lambda e: self.delete_selected_stock())

###########################################################################


    def setup_tab2(self):
        """ট্যাব ২: বিস্তারিত রিপোর্ট ও স্মার্ট ফিল্টারিং"""
        
        # --- ১. প্রধান ফিল্টার কন্ট্রোল ফ্রেম ---
        f_ctrl = tk.LabelFrame(self.t2, text=" বিস্তারিত রিপোর্ট ও ফিল্টার ", 
                               font=("Arial", 11, "bold"), bg="#f0f2f5", pady=10)
        f_ctrl.pack(fill="x", padx=20, pady=10)

        

        # --- আইটেম ও মাসিক রিপোর্ট সেকশন (Row 0) ---
        # আইটেম রিপোর্ট
        tk.Label(f_ctrl, text="আইটেম:", bg="#f0f2f5").grid(row=0, column=0, padx=5, sticky="e")
        self.combo_item_history = ttk.Combobox(f_ctrl, width=20)
        self.combo_item_history.grid(row=0, column=1, padx=2)
        
        tk.Button(f_ctrl, text="🔎 আইটেম রিপোর্ট", bg="#d35400", fg="white", 
                  font=("Arial", 9, "bold"), command=self.fetch_item_lifetime_report).grid(row=0, column=2, padx=5)

        # মাসিক রিপোর্ট (বছর ও মাস বাছুন)
        tk.Label(f_ctrl, text="বছর:", bg="#f0f2f5").grid(row=0, column=3, padx=5, sticky="e")
        self.combo_year = ttk.Combobox(f_ctrl, values=[str(y) for y in range(2020, 2031)], width=7)
        self.combo_year.set(datetime.now().strftime("%Y")) # বর্তমান বছর সেট করা
        self.combo_year.grid(row=0, column=4, padx=2)
        
        self.combo_month = ttk.Combobox(f_ctrl, values=["সব মাস", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"], width=10)
        self.combo_month.current(0)
        self.combo_month.grid(row=0, column=5, padx=2)
        
        tk.Button(f_ctrl, text="🔍 মাসিক রিপোর্ট", bg="#34495e", fg="white", 
                  font=("Arial", 9, "bold"), command=self.fetch_smart_report).grid(row=0, column=6, padx=5)

        # --- সাপ্তাহিক ও কাস্টমার রিপোর্ট সেকশন (Row 1) ---
        # তারিখ ফিল্টার
        tk.Label(f_ctrl, text="তারিখ:", bg="#f0f2f5").grid(row=1, column=0, padx=5, pady=10, sticky="e")
        self.ent_rep_date = tk.Entry(f_ctrl, width=15)
        self.ent_rep_date.grid(row=1, column=1, padx=2)
        self.ent_rep_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # সাপ্তাহিক ও নির্দিষ্ট দিনের বাটন
        tk.Button(f_ctrl, text="📅 ঐ সপ্তাহ", bg="#8e44ad", fg="white", 
                  font=("Arial", 8, "bold"), command=self.fetch_weekly_report).grid(row=1, column=2, padx=2)
        
        tk.Button(f_ctrl, text="📌 ঐ নির্দিষ্ট দিন", bg="#6c5ce7", fg="white", 
                  font=("Arial", 8, "bold"), command=self.fetch_specific_day_report).grid(row=1, column=3, padx=2)

        # কাস্টমার রিপোর্ট
        tk.Label(f_ctrl, text="কাস্টমার:", bg="#f0f2f5").grid(row=1, column=4, padx=5, sticky="e")
        self.ent_search_cust = tk.Entry(f_ctrl, width=15)
        self.ent_search_cust.grid(row=1, column=5, padx=2)
        self.ent_search_cust.bind('<KeyRelease>', lambda e: self.show_suggestions(e, 'customer_report'))

        # কাস্টমার লেজার ও এক্সেল এক্সপোর্ট বাটন
        tk.Button(f_ctrl, text="👤 কাস্টমার লেজার", bg="#2980b9", fg="white", 
                  font=("Arial", 9, "bold"), command=self.fetch_customer_report).grid(row=1, column=6, padx=5)
        
        tk.Button(f_ctrl, text="📗 Excel এক্সপোর্ট", bg="#1f7a44", fg="white", 
                  font=("Arial", 9, "bold"), command=self.export_to_excel).grid(row=1, column=7, padx=5)

        # --- ২. তারিখের রেঞ্জ ফিল্টার (Range Filter) ---
        f_range = tk.Frame(self.t2, bg="#f8f9fa", pady=5)
        f_range.pack(fill="x", padx=20)
        
        tk.Label(f_range, text="রেঞ্জ শুরু (YYYY-MM-DD):", bg="#f8f9fa").grid(row=0, column=0)
        self.ent_start_date = tk.Entry(f_range, width=12)
        self.ent_start_date.grid(row=0, column=1, padx=5)
        self.ent_start_date.insert(0, datetime.now().strftime("%Y-%m-01")) # মাসের ১ তারিখ
        
        tk.Label(f_range, text="শেষ তারিখ:", bg="#f8f9fa").grid(row=0, column=2)
        self.ent_end_date = tk.Entry(f_range, width=12)
        self.ent_end_date.grid(row=0, column=3, padx=5)
        self.ent_end_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        tk.Button(f_range, text="📊 রেঞ্জ রিপোর্ট দেখুন", bg="#16a085", fg="white", 
                  font=("Arial", 9, "bold"), command=self.load_range_summary_report).grid(row=0, column=4, padx=10)

        # --- ৩. স্ট্যাটাস ও টেবিল ভিউ ---
        self.lbl_stats = tk.Label(self.t2, text="রিপোর্ট লোড করুন...", 
                                  font=("Arial", 12, "bold"), bg="#f0f2f5", fg="#2c3e50")
        self.lbl_stats.pack(pady=10)

        # --- ৩. স্ট্যাটাস ও রিপোর্ট কার্ড সেকশন ---
        # পুরোনো lbl_stats টিকে একটি কন্টেইনার ফ্রেম দিয়ে রিপ্লেস করছি
        card_container = tk.Frame(self.t2, bg="#f0f2f5")
        card_container.pack(fill="x", padx=20, pady=10)

        # কার্ডগুলোর কমন ফন্ট
        font_header = ("Arial", 11, "bold")
        font_value = ("Verdana", 14, "bold")

        # ১. মোট কেনা কার্ড (Blue)
        self.f_buy_card = tk.Frame(card_container, bg="#3498db", relief="flat", padx=15, pady=10)
        self.f_buy_card.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(self.f_buy_card, text="🛒 মোট কেনা", bg="#3498db", fg="white", font=font_header).pack()
        self.lbl_total_buy = tk.Label(self.f_buy_card, text="৳ ০.০০", bg="#3498db", fg="white", font=font_value)
        self.lbl_total_buy.pack()

        # ২. মোট বিক্রি কার্ড (Green)
        self.f_sell_card = tk.Frame(card_container, bg="#27ae60", relief="flat", padx=15, pady=10)
        self.f_sell_card.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(self.f_sell_card, text="💰 মোট বিক্রি", bg="#27ae60", fg="white", font=font_header).pack()
        self.lbl_total_sell = tk.Label(self.f_sell_card, text="৳ ০.০০", bg="#27ae60", fg="white", font=font_value)
        self.lbl_total_sell.pack()

        # ৩. নগদ জমা কার্ড (Teal)
        self.f_cash_card = tk.Frame(card_container, bg="#16a085", relief="flat", padx=15, pady=10)
        self.f_cash_card.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(self.f_cash_card, text="💵 মোট নগদ জমা", bg="#16a085", fg="white", font=font_header).pack()
        self.lbl_total_cash = tk.Label(self.f_cash_card, text="৳ ০.০০", bg="#16a085", fg="white", font=font_value)
        self.lbl_total_cash.pack()

        # ৪. আনুমানিক লাভ কার্ড (Orange)
        self.f_profit_card = tk.Frame(card_container, bg="#e67e22", relief="flat", padx=15, pady=10)
        self.f_profit_card.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(self.f_profit_card, text="📈 আনুমানিক লাভ", bg="#e67e22", fg="white", font=font_header).pack()
        self.lbl_total_profit = tk.Label(self.f_profit_card, text="৳ ০.০০", bg="#e67e22", fg="white", font=font_value)
        self.lbl_total_profit.pack()

        # পুরোনো স্ট্যাটাস লেবেলটি কার্ডের নিচে ছোট করে রাখা হলো (অতিরিক্ত তথ্যের জন্য)
        self.lbl_stats = tk.Label(self.t2, text="ফিল্টার করে রিপোর্ট দেখুন", 
                                 font=("Arial", 10), bg="#f0f2f5", fg="#7f8c8d")
        self.lbl_stats.pack(pady=5)

        # রিপোর্ট টেবিল (Treeview)
        self.tree_rep = ttk.Treeview(self.t2, columns=("D", "T", "C", "Q", "Tot", "Paid", "Due"), show='headings')
        headers = ["তারিখ", "ধরণ", "বিবরণ/কাস্টমার", "পরিমাণ", "মোট টাকা", "জমা", "বাকি"]
        
        for col, txt in zip(self.tree_rep["columns"], headers): 
            self.tree_rep.heading(col, text=txt)
            self.tree_rep.column(col, width=120, anchor="center")
        
        self.tree_rep.pack(expand=True, fill="both", padx=20, pady=10)

############################################################################################################################################

    def setup_tab3(self):
        """ট্যাব ৩: কাস্টমার পেমেন্ট, বকেয়া এবং ডাটা ব্যাক-আপ ম্যানেজমেন্ট"""
        
        # --- ১. কাস্টমার সিলেকশন ও পেমেন্ট ফ্রেম ---
        f_search = tk.LabelFrame(self.t3, text=" বকেয়া কাস্টমার সিলেকশন ও পেমেন্ট ", 
                                 font=("Arial", 11, "bold"), bg="white", padx=15, pady=10)
        f_search.pack(fill="x", padx=20, pady=10)

        tk.Label(f_search, text="কাস্টমার নির্বাচন করুন:", bg="white").grid(row=0, column=0, sticky="w")
        self.combo_cust_list = ttk.Combobox(f_search, width=30)
        self.combo_cust_list.grid(row=0, column=1, padx=10)
        self.combo_cust_list.bind('<KeyRelease>', self.filter_customer_dropdown)
        
        tk.Button(f_search, text="🔄 রিফ্রেশ", bg="#34495e", fg="white", 
                  command=self.refresh_customer_list).grid(row=0, column=2, padx=5)
        
        tk.Button(f_search, text="🔍 হিস্টোরি", bg="#2980b9", fg="white", 
                  command=self.load_customer_due_report).grid(row=0, column=3, padx=5)

        # পেমেন্ট এন্ট্রি ছোট ফ্রেম (ডানে)
        f_pay = tk.Frame(f_search, bg="#ecf0f1", padx=10, pady=5)
        f_pay.grid(row=0, column=4, padx=20)
        tk.Label(f_pay, text="জমা টাকা:", bg="#ecf0f1").grid(row=0, column=0)
        self.ent_pay_amount = tk.Entry(f_pay, width=12)
        self.ent_pay_amount.grid(row=0, column=1, padx=5)
        tk.Button(f_pay, text="✅ সেভ", bg="#27ae60", fg="white", 
                  command=self.save_customer_payment).grid(row=0, column=2)

        # স্ট্যাটাস লেবেল
        self.lbl_cust_due = tk.Label(self.t3, text="কাস্টমার সিলেক্ট করুন", 
                                     font=("Arial", 12, "bold"), bg="#f0f2f5")
        self.lbl_cust_due.pack(pady=5)

        # --- ২. কাস্টমার পেমেন্ট টেবিল (Treeview) ---
        self.tree_cust_pay = ttk.Treeview(self.t3, columns=("ID", "D", "T", "Desc", "Tot", "P", "Due"), show='headings')
        headers = ["ID", "তারিখ", "ধরণ", "বিবরণ", "মোট টাকা", "জমা", "বাকি"]
        
        for col, txt in zip(self.tree_cust_pay["columns"], headers):
            self.tree_cust_pay.heading(col, text=txt)
            self.tree_cust_pay.column(col, width=100, anchor="center")
            
        self.tree_cust_pay.pack(expand=True, fill="both", padx=20, pady=10)
        
        # --- ৩. নিচের অ্যাকশন বাটনসমূহ (মুছুন, ব্যাক-আপ, রিস্টোর) ---
        btn_frame = tk.Frame(self.t3, bg="#f0f2f5")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text=" 🗑️  মুছুন", bg="#e74c3c", fg="white", 
                  command=self.delete_customer_history_entry).pack(side="left", padx=10)

        tk.Button(btn_frame, text="💾 এখনই ব্যাক-আপ নিন", bg="#2980b9", fg="white", 
                  font=("Arial", 10, "bold"), command=lambda: self.create_backup(manual=True)).pack(side="left", padx=10)

        tk.Button(btn_frame, text="⏪ ডাটা রিস্টোর", bg="#f39c12", fg="white", 
                  font=("Arial", 10, "bold"), command=self.restore_backup).pack(side="left", padx=10)

    # =========================================================
    # --- লজিক ফাংশনসমূহ (Core Logic Functions) ---
    # =========================================================

    def refresh_data(self):
        """স্টক টেবিল আপডেট এবং ড্রপডাউন লিস্ট রিফ্রেশ করা"""
        for row in self.tree_stock.get_children(): self.tree_stock.delete(row)
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, company, unit, stock, cost_price FROM products")
        rows = cursor.fetchall()
        for r in rows:
            tag = 'low_stock' if r[4] <= 5 else 'normal'
            self.tree_stock.insert("", "end", values=r, tags=(tag,))
        
        self.tree_stock.tag_configure('low_stock', foreground='white', background='#e74c3c')
        
        items = [f"{r[1]} - {r[2]}" for r in rows]
        self.combo_search_item['values'] = items
        self.combo_sell_item['values'] = items
        self.combo_item_history['values'] = items
        conn.close()

    def filter_stock_smart(self):
        """সার্চ অনুযায়ী স্টক ফিল্টার করা"""
        sel = self.combo_search_item.get()
        if not sel: return
        for row in self.tree_stock.get_children(): self.tree_stock.delete(row)
        n, c = sel.split(" - ")
        conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
        cursor.execute("SELECT id, name, company, unit, stock, cost_price FROM products WHERE name=? AND company=?", (n, c))
        rows = cursor.fetchall()
        t_qty, t_inv = 0, 0
        for r in rows:
            tag = 'low_stock' if r[4] <= 5 else 'normal'
            self.tree_stock.insert("", "end", values=r, tags=(tag,))
            t_qty += r[4]; t_inv += (r[4]*r[5])
        
        self.tree_stock.tag_configure('low_stock', foreground='white', background='#e74c3c')
        self.lbl_stock_summary.config(text=f"পরিমাণ: {t_qty} | ইনভেস্টমেন্ট: {t_inv:,.2f} TK")
        conn.close()

    def add_product(self):
        """নতুন মাল স্টকে যোগ করা (সর্বশেষ কেনা দাম এবং ভিন্ন তারিখ সাপোর্ট সহ)"""
        try:
            conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
            
            # ইনপুট থেকে ডাটা সংগ্রহ
            d = bn_to_en(self.entries_buy['date'].get()).strip()
            n = self.entries_buy['name'].get().strip()
            c = self.entries_buy['comp'].get().strip()
            p_val = self.entries_buy['price'].get()
            q_val = self.entries_buy['qty'].get()
            u = self.combo_unit.get()
            
            if not n or not c:
                messagebox.showwarning("সতর্কতা", "পণ্যের নাম ও কোম্পানি অবশ্যই দিতে হবে।")
                return
            
            # কেনা দাম ও পরিমাণ সংখ্যায় রূপান্তর
            p_input = float(bn_to_en(p_val))
            q_input = float(bn_to_en(q_val))

            # ১. মোট কেনা মূল্য বের করা (উদাহরণ: ১০০ ফুট * ৪৯ টাকা = ৪৯০০ টাকা)
            actual_total_cost = q_input * p_input

            # ২. পরিমাণকে বেস ইউনিটে রূপান্তর (যেমন: ১০০ ফুট -> ১২০০ ইঞ্চি)
            base_qty = self.convert_to_base_unit(q_input, u)
            
            # ৩. বেস ইউনিটের জন্য লেটেস্ট রেট বের করা (ইঞ্চির দাম)
            rate_per_base_unit = actual_total_cost / base_qty if base_qty > 0 else p_input

            # বেস ইউনিটের নাম ঠিক করা (ইঞ্চি/পিস/সেমি)
            final_unit = u
            if u in ["Foot", "Gaj", "Inch"]: final_unit = "Inch"
            elif u == "Dozen": final_unit = "Pcs"
            elif u == "Meter": final_unit = "CM"

            # ৪. ডুপ্লিকেট চেক (একই তারিখে একই পণ্য যাতে ২বার এন্ট্রি না হয় - ভুল এড়াতে)
            cursor.execute("SELECT id FROM ledger WHERE date=? AND item_name=? AND company=? AND type='Purchase'", (d, n, c))
            if cursor.fetchone():
                if not messagebox.askyesno("নিশ্চিত করুন", "এই তারিখে এই পণ্যটি একবার এন্ট্রি করা হয়েছে। আপনি কি আবারও এন্ট্রি করতে চান?"):
                    conn.close(); return

            # ৫. স্টক আপডেট (নাম এবং কোম্পানি মিলিয়ে)
            cursor.execute("SELECT id, stock FROM products WHERE name=? AND company=?", (n, c))
            existing_item = cursor.fetchone()
            
            if existing_item:
                new_stock = existing_item[1] + base_qty
                # সর্বশেষ কেনা দাম (Latest Price) দিয়ে আপডেট হবে
                cursor.execute("UPDATE products SET stock=?, cost_price=?, unit=? WHERE id=?", 
                               (new_stock, rate_per_base_unit, final_unit, existing_item[0]))
            else:
                # একদম নতুন পণ্য হলে ইনসার্ট হবে
                cursor.execute("INSERT INTO products (name, company, unit, cost_price, stock) VALUES (?, ?, ?, ?, ?)", 
                               (n, c, final_unit, rate_per_base_unit, base_qty))

            # ৬. লেজার এন্ট্রি (রিপোর্টের জন্য তারিখ অনুযায়ী আলাদা লাইন তৈরি হবে)
            cursor.execute("INSERT INTO ledger (date, item_name, company, customer, type, qty, rate, total, cash_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (d, n, c, 'Supplier', 'Purchase', base_qty, rate_per_base_unit, actual_total_cost, actual_total_cost))
            
            conn.commit(); conn.close()
            
            # ইন্টারফেস রিফ্রেশ ও কনফার্মেশন
            self.refresh_data()
            messagebox.showinfo("সফল", f"স্টক আপডেট হয়েছে!\nপণ্য: {n} ({c})\nমোট কেনা: {q_input} {u}\nমোট খরচ: {actual_total_cost:,.2f} TK")
            
            # বক্সগুলো খালি করা
            for key in ['name', 'comp', 'price', 'qty']: self.entries_buy[key].delete(0, tk.END)
            
        except Exception as e: 
            messagebox.showerror("ভুল", f"সমস্যা হয়েছে: {e}")

    # --- সাজেশন ও অটো-কমপ্লিট ফাংশন ---
    def show_suggestions(self, event, field_type):
        # এন্ট্রি বক্স থেকে টেক্সট নেওয়া
        search_term = event.widget.get().strip()
        
        # ফিল্ড অনুযায়ী সঠিক লিস্টবক্স বাছা
        if field_type == 'name': listbox = self.name_listbox
        elif field_type == 'company': listbox = self.comp_listbox
        elif field_type == 'customer_report': listbox = self.cust_listbox
        else: return

        # যদি বক্স খালি থাকে, সাজেশন বন্ধ করো
        if not search_term:
            listbox.place_forget()
            return

        # ডাটাবেজ থেকে সার্চ করা
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        
        if field_type == 'name':
            cursor.execute("SELECT DISTINCT name FROM products WHERE name LIKE ?", ('%' + search_term + '%',))
        elif field_type == 'company':
            cursor.execute("SELECT DISTINCT company FROM products WHERE company LIKE ?", ('%' + search_term + '%',))
        elif field_type == 'customer_report':
            cursor.execute("SELECT DISTINCT customer FROM ledger WHERE customer LIKE ?", ('%' + search_term + '%',))
            
        results = [row[0] for row in cursor.fetchall()]
        conn.close()

        # রেজাল্ট থাকলে লিস্টবক্স দেখাও, না থাকলে সাথে সাথে মুছে ফেলো
        if results:
            listbox.delete(0, tk.END)
            for item in results: 
                listbox.insert(tk.END, item)
            
            # এন্ট্রি বক্সের ঠিক নিচে পজিশন করা
            listbox.place(in_=event.widget, x=0, rely=1.0, relwidth=1.0)
            listbox.lift() # সবকিছুর ওপরে নিয়ে আসা
            
            # সিলেকশন ইভেন্ট বাইন্ড করা
            listbox.bind('<<ListboxSelect>>', lambda e: self.on_select_suggestion(e, event.widget, listbox))
        else:
            listbox.place_forget() # কোনো মিল না থাকলে বক্স অদৃশ্য হয়ে যাবে

    def on_select_suggestion(self, event, entry_widget, listbox):
        if listbox.curselection():
            value = listbox.get(listbox.curselection()[0])
            entry_widget.delete(0, tk.END); entry_widget.insert(0, value)
            listbox.place_forget()

    # --- ব্যাক-আপ ও রিস্টোর ফাংশন ---
    def create_backup(self, manual=False):
        try:
            import shutil
            if not os.path.exists('Backups'): os.makedirs('Backups')
            shutil.copy2('ts_hardware_ultimate.db', "Backups/latest_backup.db")
            if manual: messagebox.showinfo("সফল", "ব্যাক-আপ নেওয়া হয়েছে।")
        except Exception as e:
            if manual: messagebox.showerror("এরর", str(e))

    def generate_invoice_by_id(self, ledger_id=None):
        """ইনভয়েস আইডি দিয়ে লোগো, পেমেন্ট নম্বর ও ফুটারসহ মেমো প্রিন্ট"""
        try:
            # ১. আইডি চেক
            if not ledger_id:
                ledger_id = tk.simpledialog.askstring("ইনভয়েস প্রিন্ট", "ইনভয়েস (ID) নম্বরটি লিখুন:")
            
            if not ledger_id: return

            # ২. ডাটাবেস থেকে তথ্য সংগ্রহ
            conn = sqlite3.connect('ts_hardware_ultimate.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ledger WHERE id=?", (ledger_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                messagebox.showerror("ভুল", "এই আইডি নম্বরে কোনো ইনভয়েস পাওয়া যায়নি!")
                return

            # ৩. ক্যানভাস তৈরি
            filename = f"Invoice_{row[0]}.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            # ৪. লোগো (ক্যানভাস তৈরির পরে)
            try:
                c.drawImage("mylogo.png", 50, height - 80, width=50, height=50, mask='auto')
            except:
                pass

            # ৫. হেডার (Tayabiya Store)
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 50, "Tayabiya Store") 
            c.setFont("Helvetica", 10)
            c.drawCentredString(width/2, height - 65, "Address: Alamia Hat, Urkirchor, Raozan, Chittagong")
            c.drawCentredString(width/2, height - 78, f"Mobile: +8801885399297")
            c.line(50, height - 90, width - 50, height - 90)

            # ৬. মেমো তথ্য
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, height - 110, f"Invoice No: #{row[0]}")
            c.drawString(50, height - 125, f"Customer: {row[4]}")
            c.drawString(width - 150, height - 110, f"Date: {row[1]}")

            # ৭. টেবিল
            data = [["Description", "Qty", "Rate", "Total"],
                    [f"{row[2]} ({row[3]})", f"{row[6]}", f"{row[7]}", f"{row[8]}"]]
            
            table = Table(data, colWidths=[250, 80, 80, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            table.wrapOn(c, width, height)
            table.drawOn(c, 50, height - 200)

            # ৮. হিসাব
            c.setFont("Helvetica-Bold", 10)
            c.drawString(width - 150, height - 240, f"Total: {row[8]:,.2f}")
            c.drawString(width - 150, height - 255, f"Paid:  {row[9]:,.2f}")
            c.drawString(width - 150, height - 270, f"Due:   {(row[8]-row[9]):,.2f}")

            # ৯. বিকাশ/নগদ এবং এক্সট্রা টেক্সট (ফুটার)
            c.setStrokeColor(colors.lightgrey)
            c.line(50, 100, width - 50, 100) # নিচের দিকে একটি লাইন
            
            c.setFont("Helvetica", 9)
            c.drawString(50, 85, "Payment: Bkash/Nagad: +8801885399297")
            
            # আপনার বিশেষ টেক্সটটি একদম নিচে বামে থাকবে
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(50, 70, "Printing: Ba. I. Front") # মুদ্রনেঃ বাঃ ইঃ ফ্রন্ট

            c.drawCentredString(width/2, 50, "Thank you for choosing Tayabiya Store!")

            # ১০. সেভ ও ওপেন
            c.save()
            os.startfile(filename)
            
        except Exception as e:
            messagebox.showerror("Error", f"প্রিন্ট করতে সমস্যা হয়েছে: {e}")

    def restore_backup(self):
        try:
            import shutil
            file_path = filedialog.askopenfilename(initialdir="Backups", filetypes=(("DB files", "*.db"),))
            if file_path and messagebox.askyesno("সতর্কতা", "সব ডাটা রিপ্লেস হবে। নিশ্চিত?"):
                shutil.copy2(file_path, 'ts_hardware_ultimate.db')
                self.refresh_data()
                messagebox.showinfo("সফল", "ডাটা রিস্টোর হয়েছে।")
        except Exception as e: messagebox.showerror("এরর", str(e))

    # =========================================================
    # --- বিক্রি ও ইনভয়েস লজিক (Sales & Invoice Logic) ---
    # =========================================================
    def make_sale(self):
        """পণ্য বিক্রি করা এবং সঠিক এককে স্টক থেকে পরিমাণ কমানো"""
        try:
            conn = sqlite3.connect('ts_hardware_ultimate.db')
            cursor = conn.cursor()
            
            # ১. ইনপুট ডাটা নেওয়া ও সংখ্যায় রূপান্তর
            date = bn_to_en(self.ent_sale_date.get()).strip()
            qty_input = float(bn_to_en(self.ent_sell_qty.get() or 0))
            price = float(bn_to_en(self.ent_sell_price.get() or 0))
            cash = float(bn_to_en(self.ent_sell_cash.get() or 0))
            unit_type = self.combo_sell_unit.get() 
            cust_name = self.ent_cust_name.get().strip() or "Cash Customer"
            
            selection = self.combo_sell_item.get()
            if " - " not in selection:
                messagebox.showwarning("সতর্কতা", "দয়া করে তালিকা থেকে সঠিক পণ্য ও কোম্পানি সিলেক্ট করুন।")
                return
            
            p_name, p_comp = selection.split(" - ")

            # ২. বিক্রয় একক থেকে বেস এককে (ইঞ্চি/পিস) কনভার্ট করা
            # যদি কাস্টমার ১ ফুট নেয়, স্টক থেকে ১২ ইঞ্চি কমবে। 
            # কিন্তু কাস্টমার যদি সরাসরি ১ ইঞ্চি নেয়, তবে ১-ই কমবে।
            deduct_qty = qty_input
            conv_map = {"Foot": 12, "Dozen": 12, "Gaj": 36, "Meter": 100}
            
            if unit_type in conv_map:
                deduct_qty = qty_input * conv_map[unit_type]
            # মনে রাখবেন: যদি unit_type 'Inch' বা 'Pcs' হয়, তবে deduct_qty = qty_input-ই থাকবে।

            # ৩. স্টক চেক (নাম এবং কোম্পানি মিলিয়ে)
            cursor.execute("SELECT id, stock, unit FROM products WHERE name=? AND company=?", (p_name, p_comp))
            res = cursor.fetchone()

            if res:
                p_id, current_stock, base_unit = res
                
                if current_stock >= deduct_qty:
                    # ৪. স্টক আপডেট (কমানো)
                    cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (deduct_qty, p_id))
                    
                    # ৫. লেজারে এন্ট্রি (হিস্ট্রি রাখা)
                    total_bill = qty_input * price # এটি মেমোর মোট টাকা
                    cursor.execute("""INSERT INTO ledger (date, item_name, company, customer, type, qty, rate, total, cash_paid) 
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                   (date, p_name, p_comp, cust_name, 'Sale', qty_input, price, total_bill, cash))
                    
                    last_id = cursor.lastrowid 
                    conn.commit()
                    conn.close()
                    
                    # ৬. ইন্টারফেস আপডেট ও ইনভয়েস
                    self.refresh_data()
                    self.generate_invoice_by_id(last_id) 
                    messagebox.showinfo("সফল", f"বিক্রি সম্পন্ন!\nমেমো নম্বর: {last_id}\nস্টক থেকে কমেছে: {deduct_qty} {base_unit}")
                    
                    # ইনপুট ক্লিয়ার
                    self.ent_sell_qty.delete(0, tk.END)
                    self.ent_sell_price.delete(0, tk.END)
                    self.ent_sell_cash.delete(0, tk.END)
                    self.ent_cust_name.delete(0, tk.END)
                else: 
                    messagebox.showwarning("স্টক সংকট", f"পর্যাপ্ত স্টক নেই!\nবর্তমানে আছে: {current_stock} {base_unit}\nআপনি কমাতে চাইছেন: {deduct_qty} {base_unit}")
                    conn.close()
            else:
                messagebox.showerror("এরর", "পণ্যটি ডাটাবেজে খুঁজে পাওয়া যায়নি!")
                conn.close()
                
        except Exception as e: 
            messagebox.showerror("এরর", f"বিক্রি সম্পন্ন করা যায়নি: {e}")

    # =========================================================
    # --- রিপোর্ট ও ডিসপ্লে লজিক (Report & Display Logic) ---
    # =========================================================
    def execute_and_display(self, query, params):
        """রিপোর্ট টেবিল (Treeview) এ ডাটা দেখানো, সামারি ক্যালকুলেশন এবং কার্ড আপডেট"""
        # পুরোনো ডাটা টেবিল থেকে মুছে ফেলা
        for row in self.tree_rep.get_children(): 
            self.tree_rep.delete(row)
            
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        
        # ১. অরিজিনাল ডাটা আনা এবং এক্সপোর্টের জন্য মেমোরিতে রাখা
        cursor.execute(query + " ORDER BY date DESC", tuple(params))
        report_data = cursor.fetchall()
        
        # এই লাইনটিই এক্সপোর্ট এরর সমাধান করবে
        self.current_report_data = report_data 
        
        # ২. ইউনিট ম্যাপ তৈরি (পণ্য অনুযায়ী একক দেখানোর জন্য)
        cursor.execute("SELECT name, company, unit FROM products")
        unit_map = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        buy_total, sell_total, cash_total = 0, 0, 0
        
        for r in report_data:
            # r[2] = item_name, r[3] = company, r[5] = type
            unit = unit_map.get((r[2], r[3]), "")
            qty_display = f"{round(r[6], 2)} {unit}".strip()
            
            total_val = round(r[8], 2)
            paid_val = round(r[9], 2)
            due = round(total_val - paid_val, 2)
            
            # টেবিল এ ডাটা ইনসার্ট
            self.tree_rep.insert("", "end", values=(
                r[1], r[5], f"{r[2]} ({r[3]})", 
                qty_display, f"{total_val:.2f}", 
                f"{paid_val:.2f}", f"{due:.2f}"
            ))
            
            # কেনা, বেচা এবং নগদ জমার হিসাব আলাদা করা
            if r[5] == 'Purchase': 
                buy_total += total_val
            elif r[5] == 'Sale': 
                sell_total += total_val
                cash_total += paid_val # বিক্রির সময় কত নগদ জমা আসলো
            
        # ৩. নতুন রঙিন কার্ডগুলোতে ডাটা আপডেট করা
        profit = sell_total - buy_total
        
        self.lbl_total_buy.config(text=f"৳ {buy_total:,.2f}")
        self.lbl_total_sell.config(text=f"৳ {sell_total:,.2f}")
        self.lbl_total_cash.config(text=f"৳ {cash_total:,.2f}")
        
        # লাভের ওপর ভিত্তি করে লাভ কার্ডের রঙ পরিবর্তন
        self.lbl_total_profit.config(text=f"৳ {profit:,.2f}")
        if profit >= 0:
            self.f_profit_card.config(bg="#e67e22") # পজিটিভ লাভ (কমলা)
        else:
            self.f_profit_card.config(bg="#e74c3c") # লস হলে লাল
            
        # পুরোনো লেবেলেও একটি সামারি দেখানো (ঐচ্ছিক)
        self.lbl_stats.config(text=f"কেনা: {buy_total:,.2f} | বিক্রি: {sell_total:,.2f} | লাভ: {profit:,.2f} TK")
        
        conn.close()

    # --- বিভিন্ন রিপোর্ট ফিল্টার ---
    def fetch_smart_report(self):
        y, m = self.combo_year.get(), self.combo_month.current()
        pat = f"{y}-%" if m == 0 else f"{y}-{m:02d}%"
        
        # ১. টেবিল বা Treeview-তে ডাটা দেখানো (আগের মতোই)
        self.execute_and_display("SELECT * FROM ledger WHERE date LIKE ?", [pat])
        
        # ২. এখন কার্ডগুলোর জন্য ডাটাবেজ থেকে যোগফল (Sum) বের করা
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        
        # মোট কেনা (Purchase) হিসাব
        cursor.execute("SELECT SUM(total) FROM ledger WHERE date LIKE ? AND type='Purchase'", [pat])
        t_buy = cursor.fetchone()[0] or 0
        
        # মোট বিক্রি (Sale) হিসাব
        cursor.execute("SELECT SUM(total) FROM ledger WHERE date LIKE ? AND type='Sale'", [pat])
        t_sell = cursor.fetchone()[0] or 0
        
        # মোট নগদ জমা (Cash Received) হিসাব
        cursor.execute("SELECT SUM(cash_paid) FROM ledger WHERE date LIKE ? AND type='Sale'", [pat])
        t_cash = cursor.fetchone()[0] or 0
        
        # ৩. আনুমানিক লাভ হিসাব (বিক্রয় মূল্য - কেনা মূল্য)
        # মনে রাখবেন: এটি একটি সাধারণ লাভ হিসাব। 
        # সঠিক লাভের জন্য বিক্রিত পণ্যের কেনা দাম বিয়োগ করতে হয়।
        profit = t_sell - t_buy 
        
        conn.close()

        # ৪. এখন কার্ডগুলোর টেক্সট আপডেট করা
        self.lbl_total_buy.config(text=f"৳ {t_buy:,.2f}")
        self.lbl_total_sell.config(text=f"৳ {t_sell:,.2f}")
        self.lbl_total_cash.config(text=f"৳ {t_cash:,.2f}")
        
        # লাভ পজিটিভ হলে সবুজ/কমলা এবং নেগেটিভ (লস) হলে লাল রঙ দেখাবে
        if profit >= 0:
            self.lbl_total_profit.config(text=f"৳ {profit:,.2f}", fg="white")
            self.f_profit_card.config(bg="#e67e22") # পজিটিভ লাভ
        else:
            self.lbl_total_profit.config(text=f"৳ {profit:,.2f}", fg="white")
            self.f_profit_card.config(bg="#e74c3c") # লস হলে লাল

        self.lbl_stats.config(text=f"{y} সালের রিপোর্ট আপডেট করা হয়েছে।")

    def fetch_weekly_report(self):
        t = bn_to_en(self.ent_rep_date.get())
        try:
            end = datetime.strptime(t, "%Y-%m-%d")
            start = end - timedelta(days=6)
            self.execute_and_display("SELECT * FROM ledger WHERE date BETWEEN ? AND ?", 
                                     [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        except: 
            messagebox.showerror("ভুল", "তারিখের ফরম্যাট সঠিক নয় (YYYY-MM-DD)।")

    def fetch_customer_report(self):
        n = self.ent_search_cust.get().strip()
        self.execute_and_display("SELECT * FROM ledger WHERE customer LIKE ?", [f'%{n}%'])

    def fetch_item_lifetime_report(self):
        sel = self.combo_item_history.get()
        if " - " in sel:
            n, c = sel.split(" - ")
            self.execute_and_display("SELECT * FROM ledger WHERE item_name=? AND company=?", [n, c])

    def fetch_specific_day_report(self):
        from tkinter import simpledialog
        target = simpledialog.askstring("তারিখ", "রিপোর্ট এর তারিখ দিন (YYYY-MM-DD):", 
                                        initialvalue=datetime.now().strftime('%Y-%m-%d'))
        if target:
            target = bn_to_en(target)
            self.execute_and_display("SELECT * FROM ledger WHERE date = ?", [target])

    def filter_customer_dropdown(self, event):
        val = event.widget.get().strip().lower()
        conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT customer FROM ledger WHERE customer NOT IN ('Supplier', 'Cash')")
        names = [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()
        self.combo_cust_list['values'] = [n for n in names if val in n.lower()] if val else names
        self.combo_cust_list.event_generate('<Down>')

    def refresh_customer_list(self):
        conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT customer FROM ledger WHERE customer NOT IN ('Supplier', 'Cash')")
        self.combo_cust_list['values'] = [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()

    def load_range_summary_report(self):
        """রেঞ্জ রিপোর্ট: নির্দিষ্ট তারিখের মধ্যে ডাটা লোড ও কার্ড আপডেট"""
        s, e = self.ent_start_date.get(), self.ent_end_date.get()
        
        # ১. কুয়েরি এবং প্যারামিটার তৈরি
        # আমরা 'SELECT *' ব্যবহার করছি যাতে execute_and_display সব কলাম পায়
        query = "SELECT * FROM ledger WHERE date BETWEEN ? AND ?"
        params = [s, e]
        
        # ২. আমাদের স্মার্ট ফাংশনটিকে কল করা
        # এটিই টেবিল মুছবে, নতুন ডাটা বসাবে, কার্ড আপডেট করবে এবং এক্সপোর্টের জন্য ডাটা সেভ করবে
        self.execute_and_display(query, params)
        
        # ৩. অতিরিক্ত ফিডব্যাক (ঐচ্ছিক)
        self.lbl_stats.config(text=f"রিপোর্ট: {s} থেকে {e} তারিখ পর্যন্ত দেখা হচ্ছে।")

    # =========================================================
    # --- কাস্টমার পেমেন্ট ও ডিউ লজিক (Customer & Payment) ---
    # =========================================================
    def load_customer_due_report(self):
        """নির্দিষ্ট কাস্টমারের বকেয়া ও হিস্ট্রি লোড করা"""
        n = self.combo_cust_list.get()
        if not n: return
        
        for row in self.tree_cust_pay.get_children(): self.tree_cust_pay.delete(row)
        conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
        
        cursor.execute("SELECT id, date, type, item_name, total, cash_paid FROM ledger WHERE customer = ? ORDER BY date DESC", (n,))
        rows = cursor.fetchall()
        
        total_bill, total_paid = 0, 0
        for r in rows:
            due = r[4] - r[5]
            self.tree_cust_pay.insert("", "end", values=(r[0], r[1], r[2], r[3], f"{r[4]:.2f}", f"{r[5]:.2f}", f"{due:.2f}"))
            total_bill += r[4]; total_paid += r[5]
            
        self.lbl_cust_due.config(text=f"কাস্টমার: {n} | মোট বকেয়া: {(total_bill - total_paid):,.2f} TK")
        conn.close()

    def save_customer_payment(self):
        """বকেয়া টাকা জমা নেওয়া"""
        try:
            name = self.combo_cust_list.get()
            amount = float(bn_to_en(self.ent_pay_amount.get()))
            
            if not name or amount <= 0:
                messagebox.showwarning("সতর্কতা", "কাস্টমার এবং সঠিক টাকার পরিমাণ দিন।")
                return

            conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
            cursor.execute("""INSERT INTO ledger (date, item_name, company, customer, type, qty, rate, total, cash_paid) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (datetime.now().strftime("%Y-%m-%d"), 'Cash Received', 'N/A', name, 'Payment', 0, 0, 0, amount))
            conn.commit(); conn.close()
            
            self.ent_pay_amount.delete(0, tk.END)
            self.load_customer_due_report()
            messagebox.showinfo("সফল", "পেমেন্ট সফলভাবে জমা হয়েছে।")
        except: 
            messagebox.showerror("ভুল", "টাকার পরিমাণ সঠিক নয়।")

    # =========================================================
    # --- এক্সপোর্ট ও ডিলিট লজিক (Export & Delete Logic) ---
    # =========================================================
    def export_to_excel(self):
        """বর্তমান রিপোর্ট ডাটা এক্সেল ফাইলে সেভ করা"""
        if hasattr(self, 'current_report_data') and self.current_report_data:
            # ডাটাফ্রেম তৈরি
            df = pd.DataFrame(self.current_report_data, 
                              columns=["ID", "তারিখ", "বিবরণ", "কোম্পানি", "কাস্টমার", "ধরণ", "পরিমাণ", "দর", "মোট টাকা", "জমা"])
            
            # বকেয়া কলাম ক্যালকুলেট করা
            df['বাকি'] = df['মোট টাকা'] - df['জমা']

            # টোটাল রো (Row) তৈরি করা
            total_row = {
                "ID": "TOTAL", "তারিখ": "", "বিবরণ": "", "কোম্পানি": "", "কাস্টমার": "",
                "ধরণ": "", "পরিমাণ": "", "দর": "",
                "মোট টাকা": df['মোট টাকা'].sum(),
                "জমা": df['জমা'].sum(),
                "বাকি": df['বাকি'].sum()
            }
            
            # ডাটাফ্রেমের শেষে টোটাল রো যুক্ত করা
            df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

            # ফাইল সেভ ডায়ালগ
            default_name = f"Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            path = filedialog.asksaveasfilename(initialfile=default_name, defaultextension=".xlsx")
            
            if path: 
                df.to_excel(path, index=False)
                messagebox.showinfo("সফল", f"Excel ফাইলটি সেভ হয়েছে।\nমোট জমা: {total_row['জমা']:,.2f}\nমোট বকেয়া: {total_row['বাকি']:,.2f}")
        else: 
            messagebox.showwarning("খালি", "প্রথমে কোনো রিপোর্ট লোড করুন (যেমন: মাসিক বা কাস্টমার লেজার)।")

    def delete_selected_stock(self):
        selected = self.tree_stock.selection()
        if not selected:
            messagebox.showwarning("সিলেকশন", "দয়া করে ডিলিট করার জন্য একটি পণ্য বাছুন।")
            return
        
        if messagebox.askyesno("নিশ্চিত করুন", "আপনি কি এই পণ্যটি এবং এর যাবতীয় সব ইতিহাস (History) চিরতরে ডিলিট করতে চান?"):
            item = self.tree_stock.item(selected)
            product_id = item['values'][0]
            product_name = item['values'][1] # পণ্যের নাম

            conn = sqlite3.connect('ts_hardware_ultimate.db')
            cursor = conn.cursor()
            
            # ১. মেইন প্রোডাক্ট টেবিল থেকে ডিলিট
            cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
            
            # ২. লেজার/হিস্ট্রি টেবিল থেকে ওই পণ্যের সব রেকর্ড ডিলিট
            cursor.execute("DELETE FROM ledger WHERE item_name=?", (product_name,))
            
            conn.commit()
            conn.close()
            
            self.refresh_data()
            messagebox.showinfo("সফল", f"'{product_name}' এবং এর সব হিস্ট্রি ডিলিট করা হয়েছে।")

    def delete_customer_history_entry(self):
        """কাস্টমার লেজার থেকে নির্দিষ্ট পেমেন্ট বা ট্রানজ্যাকশন মোছা"""
        selected = self.tree_cust_pay.focus()
        if not selected: return
        data = self.tree_cust_pay.item(selected)['values']
        
        if messagebox.askyesno("নিশ্চিত?", "এই এন্ট্রিটি মুছবেন? (দ্রষ্টব্য: এটি শুধু লেজার থেকে মুছবে, স্টক অটো-সমন্বয় হবে না)"):
            conn = sqlite3.connect('ts_hardware_ultimate.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ledger WHERE id=?", (data[0],))
            conn.commit(); conn.close()
            self.load_customer_due_report()

    # =========================================================
    # ---  (History Popup & Edit) ---
    # =========================================================

    def filter_stock_by_keyword(self, event=None):
        """কি-ওয়ার্ড দিয়ে স্টক টেবিল ফিল্টার করা - কলাম সোয়াপ ফিক্সড"""
        keyword = self.ent_search_stock.get().strip()
        for row in self.tree_stock.get_children():
            self.tree_stock.delete(row)
            
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        
        # আপনার refresh_data এর মতোই এখানে কলামের নামগুলো নির্দিষ্ট করে দিন
        query = "SELECT id, name, company, unit, stock, cost_price FROM products WHERE name LIKE ? OR company LIKE ?"
        cursor.execute(query, (f'%{keyword}%', f'%{keyword}%'))
        
        for r in cursor.fetchall():
            tag = 'low_stock' if r[4] <= 5 else 'normal'
            self.tree_stock.insert("", "end", values=r, tags=(tag,))
            
        self.tree_stock.tag_configure('low_stock', foreground='white', background='#e74c3c')
        conn.close()

    def filter_item_dropdown(self, event):
        """বেচাকেনার সময় ড্রপডাউনে পণ্য ফিল্টার করা"""
        val = event.widget.get().strip().lower()
        conn = sqlite3.connect('ts_hardware_ultimate.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, company FROM products")
        all_items = [f"{r[0]} - {r[1]}" for r in cursor.fetchall()]
        conn.close()

        if val == '':
            self.combo_sell_item['values'] = all_items
        else:
            data = [item for item in all_items if val in item.lower()]
            self.combo_sell_item['values'] = data
        
        # টাইপ করার সময় ড্রপডাউন লিস্টটি খুলে যাবে
        self.combo_sell_item.event_generate('<Down>')  

    # =========================================================
    # --- হিস্ট্রি পপআপ ও এডিট লজিক (History Popup & Edit) ---
    # =========================================================
    def open_history_popup(self, event):
        """পণ্যর ওপর ডাবল ক্লিক করলে হিস্ট্রি পপআপ উইন্ডো ওপেন হবে"""
        selected = self.tree_stock.focus()
        if not selected: return
        data = self.tree_stock.item(selected)['values']
        p_name, p_comp = data[1], data[2]
        
        win = tk.Toplevel(self.root)
        win.title(f"{p_name} ({p_comp}) - বিস্তারিত হিস্ট্রি")
        win.geometry("1150x650")
        
        # ১. টেবিল অংশ
        tree_frame = tk.Frame(win)
        tree_frame.pack(expand=True, fill="both", padx=15, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=("ID", "D", "N", "C", "T", "Q", "R", "Tot"), show='headings')
        headers = ["ID", "তারিখ", "পণ্যের নাম", "কোম্পানি", "ধরণ", "পরিমাণ", "দর", "মোট"]
        for col, txt in zip(tree["columns"], headers): 
            tree.heading(col, text=txt); tree.column(col, width=110, anchor="center")
        
        sc = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sc.set)
        tree.pack(side="left", expand=True, fill="both")
        sc.pack(side="right", fill="y")
        
        def load_hist():
            for row in tree.get_children(): tree.delete(row)
            conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
            cursor.execute("SELECT id, date, item_name, company, type, qty, rate, total FROM ledger WHERE item_name=? AND company=? ORDER BY date DESC", (p_name, p_comp))
            for r in cursor.fetchall(): tree.insert("", "end", values=r)
            conn.close()

        # ২. এডিট প্যানেল
        edit_f = tk.LabelFrame(win, text=" এন্ট্রি এডিট করুন ", bg="white", padx=15, pady=10)
        edit_f.pack(fill="x", padx=15, pady=10)

        # সারি ১
        tk.Label(edit_f, text="তারিখ:", bg="white").grid(row=0, column=0)
        e_date = tk.Entry(edit_f, width=12); e_date.grid(row=0, column=1, padx=5)
        
        tk.Label(edit_f, text="পরিমাণ:", bg="white").grid(row=0, column=2)
        e_qty = tk.Entry(edit_f, width=10); e_qty.grid(row=0, column=3, padx=5)
        
        lbl_unit = tk.Label(edit_f, text="[Unit]", bg="white", fg="blue", font=("Arial", 10, "bold"))
        lbl_unit.grid(row=0, column=4, padx=2)

        tk.Label(edit_f, text="দর:", bg="white").grid(row=0, column=5)
        e_rate = tk.Entry(edit_f, width=10); e_rate.grid(row=0, column=6, padx=5)

        # সারি ২
        tk.Label(edit_f, text="পণ্যের নাম:", bg="white").grid(row=1, column=0, pady=10)
        e_pname = tk.Entry(edit_f, width=20); e_pname.grid(row=1, column=1, columnspan=2, sticky="w")
        tk.Label(edit_f, text="কোম্পানি:", bg="white").grid(row=1, column=3)
        e_pcomp = tk.Entry(edit_f, width=15); e_pcomp.grid(row=1, column=4, columnspan=2, sticky="w")

        # ৩. লজিক ফাংশনসমূহ (পপআপের ভেতরে)
        def on_tree_select(event):
            sel = tree.focus()
            if not sel: return
            v = tree.item(sel)['values']
            e_date.delete(0, tk.END); e_date.insert(0, v[1])
            e_pname.delete(0, tk.END); e_pname.insert(0, v[2])
            e_pcomp.delete(0, tk.END); e_pcomp.insert(0, v[3])
            e_qty.delete(0, tk.END); e_qty.insert(0, v[5])
            e_rate.delete(0, tk.END); e_rate.insert(0, v[6])
            
            try:
                conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
                cursor.execute("SELECT unit FROM products WHERE name=? AND company=?", (v[2], v[3]))
                res = cursor.fetchone()
                unit_text = res[0] if res else "Unit"
                lbl_unit.config(text=f"[{unit_text}]")
                conn.close()
            except: lbl_unit.config(text="[Unit]")

        tree.bind('<<TreeviewSelect>>', on_tree_select)

        def update_entry():
            """হিস্ট্রি থেকে এন্ট্রি এডিট করলে স্টক স্বয়ংক্রিয়ভাবে সমন্বয় হবে"""
            sel = tree.focus()
            if not sel: return
            v = tree.item(sel)['values']
            entry_id, old_pname, old_pcomp, old_qty, e_type = v[0], v[2], v[3], float(v[5]), v[4]
            
            try:
                conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
                cursor.execute("SELECT unit FROM products WHERE name=? AND company=?", (old_pname, old_pcomp))
                res = cursor.fetchone()
                p_unit = res[0] if res else 'Pcs'
                
                new_pname = e_pname.get().strip()
                new_pcomp = e_pcomp.get().strip()
                new_date = bn_to_en(e_date.get())
                raw_qty = float(bn_to_en(e_qty.get()))
                new_rate = float(bn_to_en(e_rate.get()))

                new_qty_converted = self.convert_to_base_unit(raw_qty, p_unit)
                new_total = new_qty_converted * new_rate
                
                # লেজার আপডেট
                cursor.execute("""UPDATE ledger SET date=?, item_name=?, company=?, qty=?, 
                                  rate=?, total=?, cash_paid=? WHERE id=?""", 
                               (new_date, new_pname, new_pcomp, new_qty_converted, new_rate, new_total, new_total, entry_id))
                
                # স্টক সমন্বয় লজিক
                qty_diff = new_qty_converted - old_qty
                
                if e_type == 'Purchase':
                    if new_pname != old_pname or new_pcomp != old_pcomp:
                        cursor.execute("UPDATE products SET stock = stock - ? WHERE name=? AND company=?", (old_qty, old_pname, old_pcomp))
                        cursor.execute("INSERT OR IGNORE INTO products (name, company, unit, cost_price, stock) VALUES (?, ?, ?, ?, 0)", (new_pname, new_pcomp, p_unit, new_rate))
                        cursor.execute("UPDATE products SET stock = stock + ?, cost_price = ? WHERE name=? AND company=?", (new_qty_converted, new_rate, new_pname, new_pcomp))
                    else:
                        cursor.execute("UPDATE products SET stock = stock + ?, cost_price = ? WHERE name=? AND company=?", (qty_diff, new_rate, old_pname, old_pcomp))
                else: # Sale
                    if new_pname != old_pname or new_pcomp != old_pcomp:
                        cursor.execute("UPDATE products SET stock = stock + ? WHERE name=? AND company=?", (old_qty, old_pname, old_pcomp))
                        cursor.execute("UPDATE products SET stock = stock - ? WHERE name=? AND company=?", (new_qty_converted, new_pname, new_pcomp))
                    else:
                        cursor.execute("UPDATE products SET stock = stock - ? WHERE name=? AND company=?", (qty_diff, old_pname, old_pcomp))
                
                conn.commit(); conn.close()
                load_hist(); self.refresh_data()
                messagebox.showinfo("সফল", "এন্ট্রি এবং স্টক আপডেট হয়েছে।")
                
            except Exception as e: 
                messagebox.showerror("ভুল", f"আপডেট ব্যর্থ: {str(e)}")

        def delete_entry():
            """হিস্ট্রি থেকে এন্ট্রি মুছলে স্টক আগের অবস্থায় ফিরে যাবে"""
            sel = tree.focus()
            if not sel or not messagebox.askyesno("নিশ্চিত", "মুছে ফেলবেন? এটি করলে স্টক সমন্বয় করা হবে।"): return
            v = tree.item(sel)['values']
            conn = sqlite3.connect('ts_hardware_ultimate.db'); cursor = conn.cursor()
            
            # স্টক রিভার্স করা
            adj = -float(v[5]) if v[4] == 'Purchase' else float(v[5])
            cursor.execute("UPDATE products SET stock = stock + ? WHERE name=? AND company=?", (adj, v[2], v[3]))
            cursor.execute("DELETE FROM ledger WHERE id=?", (v[0],))
            
            conn.commit(); conn.close()
            load_hist(); self.refresh_data()

        # বাটন পজিশন
        tk.Button(edit_f, text="✅ আপডেট", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), 
                  command=update_entry).grid(row=0, column=7, rowspan=2, padx=10, pady=5)
        tk.Button(edit_f, text="🗑️ ডিলিট", bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), 
                  command=delete_entry).grid(row=0, column=8, rowspan=2, padx=5, pady=5)
        
        load_hist()

# =========================================================
# --- মেইন অ্যাপ্লিকেশন রানার (Main Runner) ---
# =========================================================
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = HardwareApp(root)
    
    # উইন্ডো বন্ধ করার সময় কনফার্মেশন ও ব্যাক-আপ
    def on_closing():
        if messagebox.askyesno("Exit", "আপনি কি সফটওয়্যার বন্ধ করতে চান?"):
            try:
                app.create_backup() # অটো ব্যাক-আপ
            except: pass
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
    