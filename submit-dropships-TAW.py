import requests
import json
import xml.etree.ElementTree as ET

taw_u = '***REMOVED***'
taw_p = '***REMOVED***'
taw_url = '***REMOVED***'

taw_headers = {
	'Content-Type' : 'application/x-www-form-urlencoded',
	}
	
taw_xml_pt1 = """<?xml version="1.0" ?>
	<Order>
		<PONumber>po***REMOVED***5</PONumber>
		<ReqDate>12/27/19</ReqDate>
		<ShipCode>UPG</ShipCode>
		<ShipTo>				
			<Name>Test Order</Name>		
			<Address>2779 Ridgeline Dr</Address>	
			<Address>Apt 108</Address>
			<City>Corona</City>
			<State>CA</State>
			<Zip>90706</Zip>
			<Country>US</Country>
		</ShipTo>
		<Part Number="RS5118">
			<Qty>1</Qty>
		</Part>
		<Part Number="RS5116"> 
			<Qty>2</Qty>
		</Part>
		<SpecialInstructions>SPECIAL INSTRUCTIONS!!</SpecialInstructions>
		<Comment>COMMENTS!!</Comment>
   </Order>
"""

ord_headers = {
	'Authorization' : '***REMOVED***'
}

ord_url = '***REMOVED***'

ord_tag_id_drop_ready = '30063'
ord_tag_name_drop_ready = 'Dropship Ready'

ord_tag_id_drop_sent = '30064'
ord_tag_name_drop_sent = 'Dropship Sent'

ord_tag_id_drop_failed = '30067'
ord_tag_name_drop_failed = 'Dropship Request Failed'

ord_tag_id_await_tracking = '30068'
ord_tag_name_await_tracking = 'Awaiting Tracking'

### GET ALL DROPSHIP READY ORDERS FROM ORDORO ###
ord_get_dropship_orders_params = {
	'tag' : ord_tag_name_drop_ready
}

r = requests.get(f"{ord_url}/order/", params=ord_get_dropship_orders_params, headers=ord_headers)
robj = json.loads(r.content)

ord_orders = robj['order']


for eachOrder in ord_orders:
	### PARSE ORDER INFO FROM ORDORO ###
	parsed_order = {}
	parsed_order['PONumber'] = eachOrder['order_id']
	parsed_order['ReqDate'] = eachOrder['order_date'].split('T')[0]
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
		parsed_order['Parts'].append({'PartNo' : eachLine['product']['sku'], 'Qty' : eachLine['quantity']})
		
	for eachTag in eachOrder['tags']:
		if(eachTag['text'] == 'Signature Required'):
			parsed_order['SpecialInstructions'] = 'Signature Required'
	
	# {parsed_order['PONumber']}
	### CONSTRUCT XML TO SEND TO TAW ###
	xml_pt1 = f"""<?xml version='1.0' ?>
	<Order>
		<PONumber>fyz</PONumber>
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
	
	### SEND ORDER TO TAW ###
	r = requests.post(f"{taw_url}/SubmitOrder", data=f"UserID={taw_u}&Password={taw_p}&OrderInfo={full_xml}", headers=taw_headers)
	
	status = ""
	
	try:
		tree = ET.ElementTree(ET.fromstring(r.content))
		root = tree.getroot()
		status = root.find('Status').text
	except:
		status = r.content.decode('UTF-8')

	### TAG ORDERS IN ORDORO AS DROPSHIP REQUESTED ###
	if (status == "PASS"):
		print(f"Order {parsed_order['PONumber']} submitted successfully.")
		# DELETE DROPSHIP READY TAG
		r = requests.delete(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_drop_ready}/", headers=ord_headers)
		
		# ADD DROPSHIP SENT TAG
		r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_await_tracking}/", headers=ord_headers)
	else:
		print(f"Order #{parsed_order['PONumber']} failed with error: {status}")
		# DELETE DROPSHIP READY TAG
		r = requests.delete(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_drop_ready}/", headers=ord_headers)
		
		# ADD DROPSHIP FAILED TAG
		r = requests.post(f"{ord_url}/order/{parsed_order['PONumber']}/tag/{ord_tag_id_drop_failed}/", headers=ord_headers)
	
	



