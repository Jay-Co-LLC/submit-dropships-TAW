import requests
import json
import xml.etree.ElementTree as ET
import datetime

log_file = f"LOG-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"

taw_u = '***REMOVED***'
taw_p = '***REMOVED***'
taw_url = '***REMOVED***'

taw_headers = {
	'Content-Type' : 'application/x-www-form-urlencoded',
	}

ord_headers = {
	'Authorization' : '***REMOVED***',
	'Content-Type' : 'application/json'
}

ord_url = '***REMOVED***'

ord_tag_id_drop_ready = '30093'
ord_tag_name_drop_ready = 'Dropship Ready'

ord_tag_id_drop_failed = '30067'
ord_tag_name_drop_failed = 'Dropship Request Failed'

ord_tag_id_await_tracking = '30068'
ord_tag_name_await_tracking = 'Awaiting Tracking'


ord_get_dropship_orders_params = {
	'status' : 'dropshipment_requested',
	'limit' : '100'
}

def log(str):
	print(str, flush=True)
	with open(log_file, 'a') as file:
		file.write(f"{str}\n\r")

		
### GET ALL DROPSHIP READY ORDERS FROM ORDORO ###
log(f"Requesting all orders with 'Dropship Ready' from ordoro...")

r = requests.get(f"{ord_url}/order", params=ord_get_dropship_orders_params, headers=ord_headers)
robj = json.loads(r.content)

ord_orders = robj['order']

log(f"Found {len(ord_orders)} to process.\n\r\n\r")

for eachOrder in ord_orders:
	### PARSE ORDER INFO FROM ORDORO ###
	parsed_order = {}
	parsed_order['PONumber'] = eachOrder['order_number']
	
	log(f"Parsing {parsed_order['PONumber']}...")
	
	parsed_order['ReqDate'] = eachOrder['order_placed_date'].split('T')[0]
	parsed_order['ShipTo'] = {}
	parsed_order['ShipTo']['Name'] = eachOrder['shipping_address']['name']
	parsed_order['ShipTo']['Address1'] = eachOrder['shipping_address']['street1']
	parsed_order['ShipTo']['Address2'] = eachOrder['shipping_address']['street2']
	parsed_order['ShipTo']['City'] = eachOrder['shipping_address']['city']
	parsed_order['ShipTo']['State'] = eachOrder['shipping_address']['state']
	parsed_order['ShipTo']['Zip'] = eachOrder['shipping_address']['zip']
	parsed_order['ShipTo']['Country'] = eachOrder['shipping_address']['country']
	parsed_order['Parts'] = []
	
	for eachLine in eachOrder['lines']:
		parsed_order['Parts'].append({'PartNo' : eachLine['sku'], 'Qty' : eachLine['quantity']})
		
	for eachTag in eachOrder['tags']:
		if(eachTag['text'] == 'Signature Required'):
			parsed_order['SpecialInstructions'] = 'Signature Required'
	
	### CONSTRUCT XML TO SEND TO TAW ###
	xml_pt1 = f"""<?xml version='1.0' ?>
	<Order>
		<PONumber>{parsed_order['PONumber']}</PONumber>
		<ReqDate>{parsed_order['ReqDate']}</ReqDate>
		<ShipTo>				
			<Name>{parsed_order['ShipTo']['Name']}</Name>		
			<Address>{parsed_order['ShipTo']['Address1']}</Address>	
			<Address>{parsed_order['ShipTo']['Address2']}</Address>
			<City>{parsed_order['ShipTo']['City']}</City>
			<State>{parsed_order['ShipTo']['State']}</State>
			<Zip>{parsed_order['ShipTo']['Zip']}</Zip>
			<Country>{parsed_order['ShipTo']['Country']}</Country>
		</ShipTo>
	"""
	
	xml_pt2 = ""
	
	for eachPart in parsed_order['Parts']:
		xml_pt2 = f"{xml_pt2}<Part Number='{eachPart['PartNo']}'><Qty>{eachPart['Qty']}</Qty></Part>"
	
	xml_pt3 = ""
	
	try:
		xml_pt3 = f"<SpecialInstructions>{parsed_order['SpecialInstructions']}</SpecialInstructions>"
	except:
		pass
		
	xml_pt4 = "</Order>"	
	full_xml = f"{xml_pt1}{xml_pt2}{xml_pt3}{xml_pt4}"
	
	log(f"Sending XML to TAW:\n\r{full_xml}")
	
	### SEND ORDER TO TAW ###
	r = requests.post(f"{taw_url}/SubmitOrder", data=f"UserID={taw_u}&Password={taw_p}&OrderInfo={full_xml}", headers=taw_headers)
	
	status = ""
	taw_order_id = ""
	
	try:
		# PARSE XML RESPONSE FROM TAW
		tree = ET.ElementTree(ET.fromstring(r.content))
		root = tree.getroot()
		status = root.find('Status').text
		
		if (status == "PASS"):
			taw_order_id = root.find('Order').attrib['Id']
			log(f"Order submitted successfully. Order ID: {taw_order_id}")
			
			# ADD AWAITING TRACKING TAG
			log(f"Adding 'Awaiting Tracking' tag...")
			r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_await_tracking}", headers=ord_headers)
			
			# ADD COMMENT WITH TAW ORDER ID
			log(f"Adding comment with TAW Order ID {taw_order_id}")
			r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/comment", headers=ord_headers, data=json.dumps({'comment' : f'TAW_ORD_ID:{taw_order_id}'}))
		else:
			log(f"Status is not 'PASS': {status}")

			# ADD DROPSHIP FAILED TAG
			log(f"Adding 'Dropship Failed' tag...")
			r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_drop_failed}", headers=ord_headers)
	except Exception as err:
		log(f"Error parsing response. Exception:\n\r{err}\n\rLast Response:\n\r{r.content.decode('UTF-8')}")
		
		# ADD DROPSHIP FAILED TAG
		log(f"Adding 'Dropship Failed' tag...")
		r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_drop_failed}", headers=ord_headers)

	log("DONE!\n\r")
