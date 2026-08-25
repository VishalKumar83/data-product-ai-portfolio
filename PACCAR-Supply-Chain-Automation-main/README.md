# PACCAR After-Sales Supply Chain & Dealer Mapping Automation

An end-to-end automation pipeline designed to process regional dealer inventory logs, execute geospatial routing decisions, and visualize critical supply chain bottlenecks. 

🎯 **Business Impact:** This pipeline aims to optimize repetitive administrative tasks, offering a scalable template capable of reducing manual mapping overhead by up to 800 man-hours.

## 📊 Live Interactive Dashboard
🔗 **[View Live Tableau Dashboard Here](https://public.tableau.com/app/profile/jafar.khan2989/viz/PACCARAfter-SalesSupplyChainDealerMappingAutomation/Sheet1?publish=yes)]
---

## 🛠️ Tech Stack & Architecture
* **Language:** Python 3.14
* **Data Processing:** Pandas, NumPy, Openpyxl
* **Geospatial Analytics:** Geopy API (Geodesic distance mapping)
* **Business Intelligence:** Tableau Public Desktop

---

## 🚀 Key Automation Features
1. **Automated Inventory Ingestion:** Processes simulated dealer parts distribution arrays across regions to flag critical deficits (stock levels < 10 units).
2. **Geospatial Route Prioritization:** Automatically computes precise kilometers between distressed dealer nodes and the central logistics hub (Pune, India).
3. **Automated Enterprise Reporting:** Auto-generates structured, delivery-route-optimized Excel reports (`Automated_Dispatch_Report.xlsx`) instantly for logistics dispatch teams.

---

## 📁 Repository Structure
* `generate_mock_data.py`: Python engine creating regional distribution data matrices.
* `logistics_optimizer.py`: The core automation pipeline running cleaning, optimization, and reporting scripts.
* `Automated_Dispatch_Report.xlsx`: Production-ready output delivered directly to stakeholders.
