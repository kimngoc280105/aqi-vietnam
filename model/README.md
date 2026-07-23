# Du bao PM2.5 da chan troi

Thu muc nay chua pipeline chinh cho bai toan du bao dong thoi PM2.5 tu `t+1`
den `t+24`. Bo notebook va artifact du bao rieng `t+24` duoc giu trong
`model_t24/` de doi chieu.

## Thu tu chay

1. `0_multihorizon_data_preparation.ipynb`
2. `1_multihorizon_sarimax.ipynb`
3. `2_multihorizon_xgboost.ipynb`
4. `3_multihorizon_lstm.ipynb`
5. `4_multihorizon_model_selection.ipynb`

Ba notebook mo hinh doc cung file
`data/processed/pm25_training_data_enriched.csv`, tao cung 24 target theo timestamp
thuc va dung cung temporal split 70/15/15 voi purge gap 24 gio.

Notebook 4 chia Validation thanh 5 khoi thoi gian lien tiep va chon model bang
RMSE trung binh cua 24 horizon qua 5 khoi. Do lech chuan, worst-fold RMSE va MAE
la tieu chi phu. Day la blocked temporal validation audit tren cac candidate da
huan luyen; khong dung K-fold ngau nhien va khong dung Test de chon model. Test
chi duoc mo de bao cao sau khi da khoa lua chon.

Notebook 4 cung phan tich model thang cuoc theo horizon, thanh pho, learning curve,
feature importance, conformal coverage, residual, confusion matrix hau xu ly va
cac truong hop sai lon nhat. Output nam trong `model/results`, hinh nam trong
`model/figures`, saved model nam trong `model/candidates`.

SARIMAX co the chay lau vi duoc fit rieng cho ba thanh pho. LSTM can TensorFlow
va se uu tien GPU neu moi truong TensorFlow nhan duoc GPU.

`web` hien doc artifact XGBoost multi-horizon. Neu notebook 4 chon mot model
khac XGBoost thi can cap nhat backend truoc khi deploy.
