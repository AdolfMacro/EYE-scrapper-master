# 👁️ EYE Master

> **Multi-Provider Business & Point-of-Interest Discovery Platform**

**EYE Master** is a modular, extensible data discovery and scraping platform built with **Python** and **PyQt5**.
It is designed to discover, collect, validate, process, categorize, and store business and Point-of-Interest (POI) data using multiple providers through a unified architecture.

The project is designed to evolve from a traditional scraper into a **geographic business discovery and data collection framework**.

---

## 🌍 Languages

* 🇬🇧 [English](#-english)
* 🇮🇷 [فارسی](#-فارسی)
* 🇦🇲 [Հայերեն](#-հայերեն)

---

# 🇬🇧 English

## 📌 Overview

**EYE Master** is a modular business and POI discovery system focused on collecting structured geographic information from multiple data providers.

The system provides a unified architecture for:

* Search and query generation
* Multi-provider discovery
* Geographic data collection
* Data extraction and normalization
* Record validation
* Database storage
* Scraper lifecycle management
* Runtime monitoring and statistics

A core principle of the project is:

> **No Coordinates = No Record**

Location-aware records are prioritized, making geographic information an important part of the data pipeline.

---

## ✨ Features

### 🔎 Multi-Provider Discovery

EYE Master supports a provider-based architecture that allows different search and geographic data sources to be integrated without changing the core engine.

Current architecture includes providers such as:

* Google
* DuckDuckGo
* OpenStreetMap
* Balad
* Extensible custom providers

### 🧩 Keyword Matrix

Search behavior is driven by configurable keyword sources.

The system can generate deterministic search queries from keyword combinations, allowing large-scale discovery without manually creating every query.

### 📍 Geographic Validation

EYE Master is designed around geographic data.

Records can be validated and processed based on:

* Latitude
* Longitude
* Address
* Business name
* Phone numbers
* Source information

The system follows:

```text
No Coordinates = No Record
```

### 🔄 Modular Pipeline

The data-processing architecture is separated into independent stages:

```text
Configuration
      ↓
Query Generator
      ↓
Provider Manager
      ↓
Provider
      ↓
Extractor
      ↓
Validation / Pipeline
      ↓
Database
      ↓
Structured Output
```

This separation makes the system easier to maintain, debug, extend, and test.

### ⚙️ Scraper Management

EYE Master includes a process-management architecture capable of handling independent scraper processes.

Supported lifecycle operations include:

* Create
* Start
* Stop
* Restart
* Monitor
* Track runtime state

### 📊 Runtime & Statistics

Runtime information and statistics are designed to be structured and machine-readable.

This allows external applications and monitoring systems to consume:

* Process state
* Runtime statistics
* Events
* Results
* Lifecycle information

without depending on internal GUI implementation details.

### 🖥️ Graphical Interface

The project uses **PyQt5** to provide a centralized management interface.

The GUI is designed to manage:

* Scrapers
* Providers
* Keywords
* Databases
* Processes
* Runtime information
* Data management

---

## 🏗️ Architecture

```text
                         ┌──────────────────┐
                         │       GUI        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  GUI Controller  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Master / Process │
                         │     Manager      │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Scraper Process  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Scraper Worker  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Scraper Engine  │
                         └────────┬─────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      Query Generator      Provider Manager        Pipeline
                                  │                    │
                         ┌────────┼────────┐           │
                         ▼        ▼        ▼           ▼
                      Google   OSM   DuckDuckGo     Database
```

---

## 📁 Project Structure

```text
EYES-master/
│
├── categories/
│   └── business_keywords.txt
│
├── config/
│
├── database/
│
├── data/
│
├── providers/
│   ├── google/
│   ├── duckduckgo/
│   ├── osm/
│   └── ...
│
├── scraper/
│   ├── query_generator.py
│   ├── engine/
│   ├── pipeline/
│   └── ...
│
├── gui/
│
├── runtime/
│   ├── logs/
│   ├── scrapers/
│   └── databases/
│
├── main.py
└── README.md
```

---

## 🛠️ Technology Stack

| Technology            | Purpose                |
| --------------------- | ---------------------- |
| Python                | Core application       |
| PyQt5                 | Desktop GUI            |
| SQLite                | Local data storage     |
| Requests / HTTP       | Data acquisition       |
| Provider Architecture | Multi-source discovery |
| Modular Pipeline      | Data processing        |
| Process Manager       | Scraper lifecycle      |

---

## 🎯 Project Goals

EYE Master is being developed with several long-term goals:

* Build a reliable multi-provider discovery engine
* Reduce dependency on a single data source
* Create a reusable geographic data pipeline
* Normalize heterogeneous provider results
* Maintain clean and structured databases
* Support multiple independent scraper processes
* Provide machine-readable runtime information
* Make the platform extensible for future providers and data sources

---

## 🚧 Project Status

**Active Development**

The architecture is continuously evolving toward a more robust and scalable discovery platform.

---

## 👨‍💻 Author

**Mani Kamran**

Python Developer · Cybersecurity Enthusiast · Linux Explorer

---

# 🇮🇷 فارسی

## 📌 معرفی

**EYE Master** یک پلتفرم ماژولار و قابل توسعه برای **کشف، جمع‌آوری، اعتبارسنجی، پردازش و ذخیره اطلاعات کسب‌وکارها و نقاط مورد علاقه (POI)** است که با **Python** و **PyQt5** توسعه داده می‌شود.

این پروژه با استفاده از چندین Provider مختلف، داده‌های جغرافیایی و اطلاعات کسب‌وکار را در یک معماری یکپارچه جمع‌آوری و پردازش می‌کند.

هدف EYE Master این است که از یک Scraper معمولی فراتر رفته و به یک **Framework برای کشف کسب‌وکارها و جمع‌آوری داده‌های جغرافیایی** تبدیل شود.

---

## ✨ قابلیت‌ها

### 🔎 کشف اطلاعات با چند Provider

معماری پروژه به گونه‌ای طراحی شده که Providerهای مختلف بدون تغییر در هسته اصلی سیستم قابل اضافه شدن باشند.

Providerهای موجود یا در معماری پروژه شامل:

* Google
* DuckDuckGo
* OpenStreetMap
* Balad
* Providerهای سفارشی

### 🧩 سیستم Keyword

فرآیند جستجو بر اساس Keywordهای قابل تنظیم انجام می‌شود.

سیستم می‌تواند از ترکیب Keywordها، Queryهای جستجوی ساختاریافته و قابل تکرار ایجاد کند.

### 📍 اعتبارسنجی جغرافیایی

اطلاعات مکانی بخش مهمی از سیستم است.

اطلاعاتی مانند:

* Latitude
* Longitude
* آدرس
* نام کسب‌وکار
* شماره تلفن
* منبع اطلاعات

قابل پردازش و اعتبارسنجی هستند.

اصل مهم پروژه:

```text
No Coordinates = No Record
بدون مختصات = بدون رکورد
```

### 🔄 Pipeline ماژولار

پردازش داده‌ها به صورت مرحله‌ای انجام می‌شود:

```text
Configuration
      ↓
Query Generator
      ↓
Provider Manager
      ↓
Provider
      ↓
Extractor
      ↓
Validation / Pipeline
      ↓
Database
      ↓
Structured Output
```

این ساختار باعث می‌شود توسعه، تست، عیب‌یابی و اضافه کردن قابلیت‌های جدید ساده‌تر باشد.

### ⚙️ مدیریت Scraperها

سیستم مدیریت فرآیند برای کنترل Scraperهای مستقل طراحی شده است.

امکانات شامل:

* ایجاد
* اجرا
* توقف
* Restart
* مانیتورینگ
* بررسی وضعیت Runtime

### 📊 Runtime و Statistics

اطلاعات Runtime، Eventها و Statistics به صورت ساختاریافته طراحی می‌شوند تا برنامه‌های خارجی نیز بتوانند آنها را پردازش کنند.

### 🖥️ رابط گرافیکی

رابط کاربری پروژه با **PyQt5** ساخته شده و برای مدیریت بخش‌های مختلف سیستم استفاده می‌شود:

* Scraperها
* Providerها
* Keywordها
* Databaseها
* Processها
* Runtime
* Data Management

---

## 🎯 اهداف پروژه

اهداف اصلی EYE Master:

* ایجاد موتور قدرتمند کشف اطلاعات
* استفاده از چندین منبع داده
* کاهش وابستگی به یک Provider
* ساخت Pipeline استاندارد برای داده‌های جغرافیایی
* یکسان‌سازی داده‌های منابع مختلف
* مدیریت چند Scraper مستقل
* ارائه اطلاعات Runtime قابل پردازش توسط سیستم‌های خارجی
* ایجاد معماری قابل توسعه برای Providerهای آینده

---

# 🇦🇲 Հայերեն

## 📌 Նախագծի մասին

**EYE Master**-ը մոդուլային և ընդլայնվող հարթակ է, որը նախատեսված է **բիզնեսների և աշխարհագրական կետերի (POI) հայտնաբերման, հավաքագրման, վավերացման, մշակման և պահպանման** համար։

Նախագիծը մշակվում է **Python** և **PyQt5** տեխնոլոգիաներով և հնարավորություն է տալիս աշխատել տարբեր տվյալների Provider-ների հետ միասնական ճարտարապետության միջոցով։

EYE Master-ի երկարաժամկետ նպատակն է սովորական Scraper-ից վերածվել **աշխարհագրական բիզնես տվյալների հայտնաբերման և հավաքագրման ընդհանուր Framework-ի**։

---

## ✨ Հիմնական հնարավորություններ

### 🔎 Multi-Provider Discovery

Համակարգը կառուցված է Provider-ների մոդուլային ճարտարապետության վրա։

Այն հնարավորություն է տալիս ինտեգրել տարբեր տվյալների աղբյուրներ՝ առանց հիմնական Engine-ի վերաձևավորման։

Նախագծում ներառված են՝

* Google
* DuckDuckGo
* OpenStreetMap
* Balad
* Custom Provider-ներ

### 🧩 Keyword համակարգ

Որոնման գործընթացը հիմնված է կարգավորվող Keyword-ների վրա։

Համակարգը կարող է ստեղծել կառուցվածքային և deterministic որոնման Query-ներ՝ Keyword-ների տարբեր համակցություններից։

### 📍 Աշխարհագրական վավերացում

Աշխարհագրական տվյալները համակարգի կարևոր բաղադրիչն են։

Մշակվում են՝

* Latitude
* Longitude
* Հասցե
* Բիզնեսի անուն
* Հեռախոսահամար
* Տվյալների աղբյուր

Հիմնական սկզբունքը՝

```text
No Coordinates = No Record
Առանց կոորդինատների = առանց գրառման
```

### 🔄 Մոդուլային Pipeline

Տվյալների մշակումը իրականացվում է փուլերով՝

```text
Configuration
      ↓
Query Generator
      ↓
Provider Manager
      ↓
Provider
      ↓
Extractor
      ↓
Validation / Pipeline
      ↓
Database
      ↓
Structured Output
```

### ⚙️ Scraper Management

Համակարգը նախատեսված է մի քանի անկախ Scraper գործընթացների կառավարման համար։

Հնարավորություններ՝

* Ստեղծում
* Գործարկում
* Դադարեցում
* Restart
* Մոնիթորինգ
* Runtime վիճակի վերահսկում

### 📊 Runtime և Statistics

Runtime տվյալները, Event-ները և Statistics-ը նախագծվում են կառուցվածքային և մեքենայաընթեռնելի ձևաչափով, որպեսզի արտաքին ծրագրերը նույնպես կարողանան օգտագործել դրանք։

### 🖥️ Գրաֆիկական ինտերֆեյս

EYE Master-ի GUI-ն կառուցված է **PyQt5**-ով և նախատեսված է համակարգի հիմնական բաղադրիչների կառավարման համար։

---

## 🎯 Նախագծի նպատակները

EYE Master-ի հիմնական նպատակներն են՝

* Ստեղծել բազմաաղբյուր Discovery Engine
* Նվազեցնել մեկ Provider-ից կախվածությունը
* Ստեղծել աշխարհագրական տվյալների միասնական Pipeline
* Միավորել տարբեր աղբյուրներից ստացված տվյալները
* Կառավարել մի քանի անկախ Scraper գործընթացներ
* Տրամադրել արտաքին համակարգերի համար հասանելի Runtime տվյալներ
* Ստեղծել ընդլայնվող ճարտարապետություն նոր Provider-ների համար

---
---

# 📸 Screenshots

### 🖥️ EYE Master — Main Interface

![EYE Master Main Interface](https://raw.githubusercontent.com/AdolfMacro/EYE-scrapper-master/main/mapV.png)
![EYE Master Main Interface](https://raw.githubusercontent.com/AdolfMacro/EYE-scrapper-master/main/image.png)

---
## 📜 License

This project is currently under active development.
License information will be added as the project reaches its public release stage.
