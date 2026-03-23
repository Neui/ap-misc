
all: generate_apworlds_csv.apworld

generate_apworlds_csv.apworld: worlds/generate_apworlds_csv/__init__.py \
		worlds/generate_apworlds_csv/archipelago.json \
		apworlds.py
	cp apworlds.py worlds/generate_apworlds_csv/apworlds.py
	-rm generate_apworlds_csv.apworld
	cd worlds && \
		zip -9 -Z deflate ../generate_apworlds_csv.apworld \
		generate_apworlds_csv/__init__.py \
		generate_apworlds_csv/apworlds.py \
		generate_apworlds_csv/archipelago.json
