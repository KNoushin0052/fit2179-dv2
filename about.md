# Data Visualisation 2 — Submission Write-Up
**Author:** Noushin Sharmile Khan (Student ID: 34711627)  
**Date:** May 2026  
**Course:** FIT2179 Data Visualisation 2, Monash University Malaysia  

---

### i. Domain, Why, and Who (The Goal)
* **Domain:** Demographics and the birth rate collapse ("baby drought") in Malaysia (2000–2023).
* **Why:** This visualization addresses a critical national issue: the rapid decline in Malaysia's birth rate, which threatens long-term labor supply and social security. The goal is to show that this decline is not uniform, but rather is split along clear geographic, socioeconomic, and ethnic divides. By mapping birth rates alongside household income and poverty, the page transforms raw demographic statistics into a clear story about how urban wealth suppresses fertility.
* **Who:** The visualization is designed for the average Malaysian. It avoids dense academic jargon and advanced statistical concepts (such as confidence intervals or standard deviation) that would alienate a general audience. Instead, it uses clean layouts, readable labels, and intuitive metrics (like live births, birth rate per 1,000 people, and median household income in RM) to make the insights easily accessible.

### ii. What: The Data (Sources, Relevance, and Process)
The visualization combines and analyzes real-world datasets from two distinct official government sources:
1. **Department of Statistics Malaysia (DOSM) Open Data Portal** (*open.dosm.gov.my*): Vital Statistics database (2000–2023), specifically live births by state, sex, and ethnicity.
2. **DOSM Household Income & Expenditure Survey (HIES) 2022:** Data on median/mean household income, Gini coefficients, and poverty rates by state.
These datasets are highly reliable, clean, and represent the most recent public records. The data was wrangled by joining birth records with state-level economic indicators, allowing a direct comparison between fertility trends and economic development.

### iii. How: Rationale for Idioms and Interactive Features
A variety of twelve visualization idioms were selected using Munzer's framework to support specific user exploration tasks:
* **Chart 1 (Area Trend with Rules & Annotations):** Explores the national temporal trend. Dashed vertical rules highlight key socioeconomic milestones (e.g., the COVID-19 pandemic) that correlate with birth dips.
* **Chart 2 (Dumbbell/Slope Chart) & Chart 3 (Arrow Diverging Bar Chart):** Emphasize change. The dumbbell circles show starting (2000) and ending (2023) birth rates, while the diverging bar arrows show the direction and magnitude of growth/decline, isolating Terengganu as the sole increasing state.
* **Chart 4 (Animated Bubble Chart):** Uses spatial position (income vs. birth rate) and circle size (poverty rate) to show how demographic and economic factors interact. The time slider allows users to watch states migrate over a 24-year period, with a dynamic regression line tracking the yearly trend.
* **Chart 11 (Radar Chart):** Supports multidimensional state comparison. By mapping five key states across five normalized metrics, users can trace their unique socioeconomic profiles. Spoke lines, concentric rings, and a closed loop make the radar geometry clear.
* **Chart 5 (Choropleth Map):** Uses spatial location (Mercator projection) to illustrate the geography of birth rates. The interactive time slider allows users to drag through years (2000–2023) and watch the national birth rate systematically fade.
* **Chart 6 (Small Multiples Faceted Donut) & Chart 7 (Streamgraph):** Show composition. Stream graph layers present the relative change in ethnic births nationally (Malay vs. Chinese), while small multiple donuts show regional ethnic makeup in 2023.
* **Chart 8 (Dumbbell Share) & Chart 9 (Heatmap):** Illustrate the collapse of Chinese births (from 21.5% to 9.8% of national births). The heatmap cells represent birth shares by year and state, using color saturation to show the decline.
* **Chart 10 (Scatter Plot with Regression Line):** Displays correlation, using spatial coordinates to confirm the negative relationship between state income and birth rate.
* **Chart 12 (Bump Chart) & Chart 13 (Line Chart):** Show ranking and comparison. The bump chart tracks ordinal ranks over time (KL falling to last), while the line chart illustrates the widening gap between Bumiputera Malay and Chinese births.

*All charts include interactive tooltips to maximize data-ink ratio and support detail-on-demand query tasks.*
