import pandas as pd

original = pd.read_csv("data/processed/legs.csv")

train = pd.read_csv("data/datasplit/train_legs_v1.csv")
cal = pd.read_csv("data/datasplit/calibration_legs_v1.csv")
test = pd.read_csv("data/datasplit/test_legs_v1.csv")

print("RECORD COUNT CHECK")

print("Original:", len(original))
print("Train + Calibration + Test:",
      len(train) + len(cal) + len(test))

print("\nTRIP OVERLAP CHECK")

train_ids = set(train["trip_uuid"])
cal_ids = set(cal["trip_uuid"])
test_ids = set(test["trip_uuid"])

print("Train ∩ Calibration:", len(train_ids & cal_ids))
print("Train ∩ Test:", len(train_ids & test_ids))
print("Calibration ∩ Test:", len(cal_ids & test_ids))

print("\nDUPLICATE ROW CHECK")

print("Train duplicates:", train.duplicated().sum())
print("Calibration duplicates:", cal.duplicated().sum())
print("Test duplicates:", test.duplicated().sum())

print("\nCHRONOLOGICAL CHECK")

for name, data in [
    ("Train", train),
    ("Calibration", cal),
    ("Test", test)
]:
    dates = pd.to_datetime(data["trip_creation_time"])
    print(name, ":", dates.min(), "to", dates.max())