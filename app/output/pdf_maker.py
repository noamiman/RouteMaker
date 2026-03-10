import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import urllib.parse
import qrcode
import os


class GoogleMapsIntegrator:
    def __init__(self, dataframe):
        # copy the dataframe and clean column names
        self.df = dataframe.copy()
        self.df.columns = self.df.columns.str.strip().str.lower()

    def generate_directions_url(self):
        """
        Generates a Google Maps directions URL that includes all the places in the itinerary as stops.
        :return: A URL string that can be used to open Google Maps with the directions.
        """
        base_url = "https://www.google.com/maps/dir/"
        stops = []
        for _, row in self.df.iterrows():
            destination = f"{row['place']}, {row['country']}"
            stops.append(urllib.parse.quote(destination))
        return base_url + "/".join(stops)

    def create_kml_file(self, filename="itinerary_map.kml"):
        kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document><name>Travel Itinerary Map</name>"""
        kml_footer = """</Document></kml>"""

        placemarks = ""
        for _, row in self.df.iterrows():
            name = str(row['place']).replace("&", "&")
            desc = str(row.get('description', '')).replace("&", "&")
            link = str(row.get('google_maps_url', '#')).replace("&", "&")

            placemarks += f"""
    <Placemark>
      <name>{name}</name>
      <description><![CDATA[{desc}<br><br><a href="{link}">Open in Google Maps</a>]]></description>
      <address>{name}, {row['country']}</address>
    </Placemark>"""

        full_kml = kml_header + placemarks + kml_footer
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_kml)
        return filename


class pdfMaker:
    def __init__(self, data_source, customer_name="Traveler", route_url=None, stations_data=None):
        # data_source can be either a path to a CSV file or a DataFrame
        if isinstance(data_source, str):
            self.df = pd.read_csv(data_source)
        else:
            self.df = data_source

        self.df.columns = self.df.columns.str.strip().str.lower()
        # clean all string columns in the main dataframe to ensure no unsupported characters for PDF rendering
        self.df = self.df.map(lambda x: self._clean_text(x) if isinstance(x, str) else x)

        if stations_data is not None:
            self.stations_df = stations_data.copy()
            self.stations_df.columns = self.stations_df.columns.str.strip().str.lower()
            self.stations_df = self.stations_df.map(lambda x: self._clean_text(x) if isinstance(x, str) else x)
        else:
            self.stations_df = None

        self.customer_name = customer_name
        self.route_url = route_url

        # categories for ratings - these should match the columns in the dataframe that contain the ratings
        self.categories = ['romance', 'family', 'cost', 'nature', 'adventure',
                           'culture', 'food', 'relaxation', 'service', 'accessibility']

        self.colors = {
            'primary': (41, 128, 185), 'secondary': (26, 188, 156),
            'text_main': (44, 62, 80), 'text_light': (127, 140, 141),
            'bg_card': (248, 249, 250), 'bar_fill': (46, 204, 113),
            'cta': (231, 76, 60), 'bg_footer': (236, 240, 241)
        }

    def _clean_text(self, text):
        """
        Cleans the input text by:
        1. Replacing "smart" quotes and dashes with standard ones.
        2. Removing emojis and characters outside the Latin-1 range (0-255).
         This ensures compatibility with the built-in PDF fonts and prevents rendering issues.
        """
        if not isinstance(text, str):
            return str(text)

        # replacement dict
        replacements = {
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2013': "-", '\u2014': "-", '\xb0': " deg "
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)

        # remove emojis and unsupported characters by keeping only those in the Latin-1 range
        cleaned = "".join(c for c in text if ord(c) < 256)

        return cleaned.strip()

    def _generate_qr(self, url):
        """
            Generates a QR code image for the given URL and saves it as a temporary file.
        :param url: The URL to encode in the QR code.
        :return: The file path of the saved QR code image, or None if generation fails.
        """
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            temp_path = "temp_qr_code.png"
            img.save(temp_path)
            return temp_path
        except:
            return None

    def _draw_header(self, pdf, qr_file):
        pdf.set_fill_color(*self.colors['primary'])
        pdf.rect(0, 0, 210, 65, 'F')
        pdf.set_font("helvetica", 'B', 28)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(15, 12)
        pdf.cell(140, 12, "TRAVEL ITINERARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", 'I', 11)
        pdf.set_text_color(200, 230, 255)
        pdf.set_x(15)
        pdf.cell(140, 8, f"Prepared for {self.customer_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if self.route_url:
            pdf.ln(3)
            pdf.set_x(15)
            pdf.set_fill_color(*self.colors['cta'])
            pdf.set_font("helvetica", 'B', 9)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(60, 10, "START DIGITAL ROUTE >", fill=True, link=self.route_url)

        if qr_file:
            pdf.image(qr_file, x=165, y=10, w=30)
            pdf.set_xy(165, 41)
            pdf.set_font("helvetica", 'B', 7)
            pdf.set_text_color(200, 230, 255)
            pdf.cell(30, 5, "SCAN TO MAP", align='C')

    def _draw_modern_rating(self, pdf, label, value):
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0

        pdf.set_font("helvetica", '', 7.5)
        pdf.set_text_color(*self.colors['text_light'])
        pdf.cell(22, 5, f"{label.capitalize()}", new_x=XPos.RIGHT, new_y=YPos.TOP)

        curr_x, curr_y = pdf.get_x(), pdf.get_y() + 2
        pdf.set_fill_color(230, 233, 237)
        pdf.rect(curr_x, curr_y, 30, 1.2, 'F')

        pdf.set_fill_color(*self.colors['bar_fill'])
        width = (min(val, 10) / 10) * 30
        pdf.rect(curr_x, curr_y, width, 1.2, 'F')

        pdf.set_x(curr_x + 32)
        pdf.set_font("helvetica", 'B', 7.5)
        pdf.set_text_color(*self.colors['text_main'])
        pdf.cell(5, 5, f"{int(val)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def create_pdf(self, output_filename="travel_itinerary.pdf"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        qr_file = self._generate_qr(self.route_url) if self.route_url else None
        self._draw_header(pdf, qr_file)

        pdf.set_y(75)
        current_day = None

        for index, row in self.df.iterrows():
            # day separation logic - if the current row has a different 'day' value than the last one, we add a new section header
            day_in_row = row.get('day', 1)
            if day_in_row != current_day:
                if current_day is not None:
                    pdf.add_page()
                    pdf.set_y(20)
                current_day = day_in_row
                pdf.set_fill_color(*self.colors['secondary'])
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("helvetica", 'B', 16)
                pdf.cell(190, 12, f"  DAY {current_day}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(5)

            if pdf.get_y() > 210:
                pdf.add_page()
                pdf.set_y(20)

            start_y = pdf.get_y()
            pdf.set_fill_color(*self.colors['bg_card'])
            pdf.rect(10, start_y, 190, 75, 'F')
            pdf.set_fill_color(*self.colors['secondary'])
            pdf.rect(10, start_y, 1.5, 75, 'F')

            # place content
            pdf.set_xy(15, start_y + 8)
            pdf.set_font("helvetica", 'B', 16)
            pdf.set_text_color(*self.colors['text_main'])
            pdf.cell(0, 10, f"{index + 1}. {str(row['place']).upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_x(15)
            pdf.set_font("helvetica", 'B', 10)
            pdf.set_text_color(*self.colors['secondary'])
            pdf.cell(0, 5, f" {row['country']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.ln(2)
            pdf.set_x(15)
            pdf.set_font("helvetica", '', 9)
            pdf.set_text_color(*self.colors['text_main'])
            # description might be long, so we use multi_cell to wrap it within the card
            desc = row.get('description', '')
            pdf.multi_cell(100, 4.5, str(desc))

            pdf.set_y(start_y + 65)
            pdf.set_x(15)
            pdf.set_font("helvetica", 'B', 8)
            pdf.set_text_color(*self.colors['primary'])
            pdf.cell(40, 5, " EXPLORE ON GOOGLE MAPS >", link=row.get('google_maps_url', '#'))

            # rates
            ratings_x = 125
            pdf.set_y(start_y + 12)
            for cat in self.categories:
                pdf.set_x(ratings_x)
                self._draw_modern_rating(pdf, cat, row.get(cat, 0))

            pdf.set_y(start_y + 85)

        if self.stations_df is not None and not self.stations_df.empty:
            self._add_stations_page(pdf)

        pdf.output(output_filename)
        if qr_file and os.path.exists(qr_file):
            os.remove(qr_file)

    def _add_stations_page(self, pdf):
        pdf.add_page()
        pdf.set_fill_color(*self.colors['primary'])
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_y(15);
        pdf.set_font("helvetica", 'B', 22);
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "KEY STATIONS & EMERGENCY", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(50)
        for _, row in self.stations_df.iterrows():
            if pdf.get_y() > 240: pdf.add_page(); pdf.set_y(20)
            curr_y = pdf.get_y()
            pdf.set_fill_color(*self.colors['bg_footer']);
            pdf.rect(10, curr_y, 190, 35, 'F')
            pdf.set_fill_color(*self.colors['primary']);
            pdf.rect(10, curr_y, 1.5, 35, 'F')

            pdf.set_xy(17, curr_y + 5);
            pdf.set_font("helvetica", 'B', 12);
            pdf.set_text_color(*self.colors['text_main'])
            pdf.cell(0, 6, str(row.get('station name', 'Unknown')).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_x(17);
            pdf.set_font("helvetica", '', 8.5);
            pdf.set_text_color(60, 70, 80)
            pdf.multi_cell(125, 4.5, str(row.get('description', '')))

            pdf.set_xy(17, curr_y + 26);
            pdf.set_font("helvetica", 'B', 8.5);
            pdf.set_text_color(*self.colors['text_light'])
            pdf.cell(0, 6, f"CONTACT: {row.get('phone', 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_xy(150, curr_y + 11);
            pdf.set_fill_color(*self.colors['secondary']);
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("helvetica", 'B', 8);
            pdf.cell(45, 10, "NAVIGATE >", align='C', fill=True, link=row.get('google maps link', '#'))
            pdf.set_y(curr_y + 40)


# --- example ---
if __name__ == "__main__":
    # load the file
    try:
        df_test = pd.read_csv("../../ScrapedData/Bucketlistly/Thailand/Exploring_Sakon_Nakhon_10_Best_enriched.csv")

        # make the maps
        integrator = GoogleMapsIntegrator(df_test)
        full_url = integrator.generate_directions_url()
        integrator.create_kml_file("nan_loop_map.kml")

        stations_data = {
            'Station Name': ['Central Hospital', 'Tourist Police', 'Main Train Station'],
            'Description': [
                'Main medical center in the city, 24/7 ER services.',
                'English-speaking officers available for any security issue.',
                'Hub for all intercity trains and the Airport Rail Link.'
            ],
            'Phone': ['+66 2 222 2222', '1155', '+66 2 333 3333'],
            'Google Maps Link': ['...', '...', '...']
        }
        df_stations = pd.DataFrame(stations_data)

        # make pdf
        maker = pdfMaker(df_test, customer_name="Avi Ron", route_url=full_url, stations_data=df_stations)
        maker.create_pdf("Travel_Itinerary_Nan_Loop.pdf")
        print("Success! PDF and KML created.")

    except FileNotFoundError:
        print("CSV file not found. Please check the path.")
    except Exception as e:
        print(f"An error occurred: {e}")