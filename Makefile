
all: generate_csv.apworld

generate_csv.apworld: worlds/generate_csv/__init__.py \
		worlds/generate_csv/archipelago.json \
		apworlds.py
	cp apworlds.py worlds/generate_csv/apworlds.py
	-rm generate_csv.apworld
	cd worlds && \
		zip -9 -Z deflate ../generate_csv.apworld \
		generate_csv/__init__.py \
		generate_csv/apworlds.py \
		generate_csv/archipelago.json
