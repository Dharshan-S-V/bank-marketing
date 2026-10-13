# Dataset: Bank Marketing (UCI Machine Learning Repository, id 222)

* **File used:** `raw/bank-full.csv` (semicolon-separated, 45,211 rows x 17 columns = 16 inputs + target `y`)
* **Page:** https://archive.ics.uci.edu/dataset/222/bank+marketing
* **Citation:** Moro, S., Cortez, P., & Rita, P. (2014). A data-driven approach to predict the success of bank telemarketing. *Decision Support Systems, 62*, 22-31. https://doi.org/10.1016/j.dss.2014.03.001
* **Licence:** see the licence statement on the UCI dataset page (please cite the paper above when reusing the data).
* **Ordering:** the file is ordered by date (May 2008 - November 2010) according to the UCI documentation.
* **SHA-256 of the analysed file:** `d1513ec63b385506f7cfce9f2c5caa9fe99e7ba4e8c3fa264b3aaf0f849ed32d`

## How the data is obtained
`python -m src.data_loader` (also called automatically by every script) downloads the file if it is missing:
1. from the official UCI archive (`https://archive.ics.uci.edu/static/public/222/bank+marketing.zip`, nested zip), then
2. from a GitHub mirror of the same file if UCI is unreachable.

Every download is validated (shape 45,211 x 17, expected column names, `y` in {yes, no}).
The copy in this repository was obtained via the mirror because the execution sandbox could not reach UCI.

## Manual fallback
Download `bank.zip` from the UCI page, extract `bank-full.csv` and place it at `data/raw/bank-full.csv`.

## Data dictionary
See `data_dictionary.csv` (17 fields) - field descriptions follow the UCI documentation.
