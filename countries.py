import difflib
import re
from dataclasses import dataclass
from html import escape as html_escape


def escape(text: str) -> str:
    return html_escape(text, quote=False)

from utils import format_quote

_APOSTROPHES = "'’‘`ʻʼ"
_CURRENCY_TEXT = """
AED|BAA dirhami
AFN|Afg'on afg'onisi
ALL|Albaniya leki
AMD|Armaniston drami
ANG|Niderland antil guldeni
AOA|Angola kvanzasi
ARS|Argentina pesosi
AUD|Avstraliya dollari
AWG|Aruba florini
AZN|Ozarbayjon manati
BAM|Bosniya markasi
BBD|Barbados dollari
BDT|Bangladesh takasi
BGN|Bolgar levi
BHD|Bahrayn dinori
BIF|Burundi franki
BMD|Bermuda dollari
BND|Bruney dollari
BOB|Boliviya bolivianosi
BRL|Braziliya reali
BSD|Bagama dollari
BTN|Butan ngultrumi
BWP|Botsvana pulasi
BYN|Belarus rubli
BZD|Beliz dollari
CAD|Kanada dollari
CDF|Kongo franki
CHF|Shveytsariya franki
CLF|Chili hisob birligi
CLP|Chili pesosi
CNH|Xitoy yuani (ofshor)
CNY|Xitoy yuani
COP|Kolumbiya pesosi
CRC|Kosta-Rika koloni
CUP|Kuba pesosi
CVE|Kabo-Verde eskudosi
CZK|Chexiya kronasi
DJF|Jibuti franki
DKK|Daniya kronasi
DOP|Dominikana pesosi
DZD|Jazoir dinori
EGP|Misr funti
ERN|Eritreya nakfasi
ETB|Efiopiya birri
EUR|Yevro
FJD|Fiji dollari
FKP|Folklend funti
FOK|Farer kronasi
GBP|Britaniya funti
GEL|Gruziya larisi
GGP|Gernsi funti
GHS|Gana sedisi
GIP|Gibraltar funti
GMD|Gambiya dalasisi
GNF|Gvineya franki
GTQ|Gvatemala ketsali
GYD|Gayana dollari
HKD|Gonkong dollari
HNL|Gonduras lempirasi
HRK|Xorvat kunasi
HTG|Gaiti gurdi
HUF|Vengriya forinti
IDR|Indoneziya rupiyasi
ILS|Isroil shekeli
IMP|Men oroli funti
INR|Hind rupiyasi
IQD|Iroq dinori
IRR|Eron riali
ISK|Islandiya kronasi
JEP|Jersi funti
JMD|Yamayka dollari
JOD|Iordaniya dinori
JPY|Yaponiya iyenasi
KES|Keniya shillingi
KGS|Qirg'iz somi
KHR|Kambodja rieli
KID|Kiribati dollari
KMF|Komor franki
KPW|Shimoliy Koreya voni
KRW|Koreya voni
KWD|Quvayt dinori
KYD|Kayman dollari
KZT|Qozog'iston tengesi
LAK|Laos kipi
LBP|Livan funti
LKR|Shri-Lanka rupiyasi
LRD|Liberiya dollari
LSL|Lesoto lotisi
LYD|Liviya dinori
MAD|Marokash dirhami
MDL|Moldova leyi
MGA|Malagasi ariarisi
MKD|Shimoliy Makedoniya denari
MMK|Myanma kyati
MNT|Mongoliya tugriki
MOP|Makao patakasi
MRU|Mavritaniya ugiyasi
MUR|Mavrikiy rupiyasi
MVR|Maldiv rufiyasi
MWK|Malavi kvachasi
MXN|Meksika pesosi
MYR|Malayziya ringgiti
MZN|Mozambik metikali
NAD|Namibiya dollari
NGN|Nigeriya nayrasi
NIO|Nikaragua kordobasi
NOK|Norvegiya kronasi
NPR|Nepal rupiyasi
NZD|Yangi Zelandiya dollari
OMR|Ummon riali
PAB|Panama balboasi
PEN|Peru soli
PGK|Papua-Yangi Gvineya kinasi
PHP|Filippin pesosi
PKR|Pokiston rupiyasi
PLN|Polsha zlotiysi
PYG|Paragvay guaranisi
QAR|Qatar riali
RON|Ruminiya leyi
RSD|Serbiya dinori
RUB|Rossiya rubli
RWF|Ruanda franki
SAR|Saudiya riali
SBD|Solomon orollari dollari
SCR|Seyshel rupiyasi
SDG|Sudan funti
SEK|Shvetsiya kronasi
SGD|Singapur dollari
SHP|Avliyo Yelena funti
SLE|Sierra-Leone leonesi
SLL|Sierra-Leone leonesi (eski)
SOS|Somali shillingi
SRD|Surinam dollari
SSP|Janubiy Sudan funti
STN|San-Tome dobrasi
SYP|Suriya funti
SZL|Esvatini lilangenisi
THB|Tailand bati
TJS|Tojikiston somonisi
TMT|Turkmaniston manati
TND|Tunis dinori
TOP|Tonga paangasi
TRY|Turk lirasi
TTD|Trinidad va Tobago dollari
TVD|Tuvalu dollari
TWD|Tayvan dollari
TZS|Tanzaniya shillingi
UAH|Ukraina grivnasi
UGX|Uganda shillingi
USD|AQSH dollari
UYU|Urugvay pesosi
UZS|O'zbek so'mi
VES|Venesuela bolivari
VND|Vetnam dongi
VUV|Vanuatu vatusi
WST|Samoa talasi
XAF|Markaziy Afrika franki
XCD|Sharqiy Karib dollari
XCG|Karib guldeni
XDR|Maxsus qarz olish huquqi
XOF|G'arbiy Afrika franki
XPF|Fransuz Tinch okeani franki
YER|Yaman riali
ZAR|Janubiy Afrika randi
ZMW|Zambiya kvachasi
ZWG|Zimbabve oltini
ZWL|Zimbabve dollari
"""

CURRENCY_NAMES = dict(
    line.split("|", 1) for line in _CURRENCY_TEXT.strip().splitlines() if line.strip()
)

_CODE_FLAGS = {
    "USD": "💵",
    "EUR": "💶",
    "GBP": "💷",
    "JPY": "💴",
    "CNY": "💴",
    "UZS": "🇺🇿",
    "RUB": "🇷🇺",
    "KRW": "🇰🇷",
    "TRY": "🇹🇷",
    "KZT": "🇰🇿",
}


@dataclass(frozen=True)
class Place:
    flag: str
    name: str
    currency: str
    aliases: tuple[str, ...] = ()
    note: str = ""
    kind: str = "country"


def _rows(block: str) -> list[Place]:
    places = []
    for line in block.strip().splitlines():
        if not line.strip():
            continue
        flag, name, currency, note, aliases = line.split("\t")
        extra = tuple(item.strip() for item in aliases.split(",") if item.strip())
        places.append(Place(flag, name, currency, extra, note))
    return places


# flag, o'zbekcha nom, valyuta, izoh, qo'shimcha nomlar
_PLACE_TEXT = """
🇺🇿	O'zbekiston	UZS		uzbekistan,uzbekiston,узбекистан,ўзбекистон,som,so'm,сум,uz
🇰🇿	Qozog'iston	KZT		kazakhstan,qozogiston,казахстан,қозоғистон,tenge,тенге,kz
🇰🇬	Qirg'iziston	KGS		kyrgyzstan,kyrgyz,qirgiziston,киргизия,кыргызстан,kg
🇹🇯	Tojikiston	TJS		tajikistan,tochikiston,таджикистан,tj
🇹🇲	Turkmaniston	TMT		turkmenistan,туркменистан,tm
🇦🇿	Ozarbayjon	AZN		azerbaijan,озарбайджан,азербайджан,az
🇦🇲	Armaniston	AMD		armenia,армения,am
🇬🇪	Gruziya	GEL		georgia,грузия,sakartvelo,ge
🇷🇺	Rossiya	RUB		russia,russian,россия,рф,rubl,рубль,ru
🇺🇦	Ukraina	UAH		ukraine,украина,ua
🇧🇾	Belarus	BYN		belarus,беларусь,белоруссия,by
🇲🇩	Moldova	MDL		moldova,молдова,молдавия,md
🇬🇧	Buyuk Britaniya	GBP		uk,britain,great britain,england,angliya,britaniya,shotlandiya,уэльс,великобритания,англия,британия,funt,фунт,pound,gb
🇨🇭	Shveytsariya	CHF		switzerland,швейцария,schweiz,ch
🇳🇴	Norvegiya	NOK		norway,норвегия,no
🇸🇪	Shvetsiya	SEK		sweden,швеция,se
🇩🇰	Daniya	DKK		denmark,дания,dk
🇮🇸	Islandiya	ISK		iceland,исландия,is
🇵🇱	Polsha	PLN		poland,польша,polska,pl
🇨🇿	Chexiya	CZK		czechia,czech,чехия,cz
🇭🇺	Vengriya	HUF		hungary,венгрия,hu
🇷🇴	Ruminiya	RON		romania,румыния,ro
🇷🇸	Serbiya	RSD		serbia,сербия,rs
🇧🇦	Bosniya va Gertsegovina	BAM		bosnia,босния,ba
🇦🇱	Albaniya	ALL		albania,албания,al
🇲🇰	Shimoliy Makedoniya	MKD		macedonia,north macedonia,македония,mk
🇹🇷	Turkiya	TRY		turkey,турция,turkiye,türkiye,tr
🇪🇺	Yevropa	EUR		yevro,yevropa,euro,евро,европа,eurozone,yevrozona
🇩🇪	Germaniya	EUR	Bu davlat yevrodan foydalanadi.	germany,германия,deutschland,de
🇫🇷	Fransiya	EUR	Bu davlat yevrodan foydalanadi.	france,франция,fr
🇮🇹	Italiya	EUR	Bu davlat yevrodan foydalanadi.	italy,италия,it
🇪🇸	Ispaniya	EUR	Bu davlat yevrodan foydalanadi.	spain,испания,es
🇵🇹	Portugaliya	EUR	Bu davlat yevrodan foydalanadi.	portugal,португалия,pt
🇳🇱	Niderlandiya	EUR	Bu davlat yevrodan foydalanadi.	netherlands,holland,голландия,нидерланды,nl
🇧🇪	Belgiya	EUR	Bu davlat yevrodan foydalanadi.	belgium,бельгия,be
🇦🇹	Avstriya	EUR	Bu davlat yevrodan foydalanadi.	austria,австрия,at
🇮🇪	Irlandiya	EUR	Bu davlat yevrodan foydalanadi.	ireland,ирландия,ie
🇬🇷	Gretsiya	EUR	Bu davlat yevrodan foydalanadi.	greece,греция,gr
🇫🇮	Finlandiya	EUR	Bu davlat yevrodan foydalanadi.	finland,финляндия,fi
🇸🇰	Slovakiya	EUR	Bu davlat yevrodan foydalanadi.	slovakia,словакия,sk
🇸🇮	Sloveniya	EUR	Bu davlat yevrodan foydalanadi.	slovenia,словения,si
🇪🇪	Estoniya	EUR	Bu davlat yevrodan foydalanadi.	estonia,эстония,ee
🇱🇻	Latviya	EUR	Bu davlat yevrodan foydalanadi.	latvia,латвия,lv
🇱🇹	Litva	EUR	Bu davlat yevrodan foydalanadi.	lithuania,литва,lt
🇱🇺	Lyuksemburg	EUR	Bu davlat yevrodan foydalanadi.	luxembourg,люксембург,lu
🇲🇹	Malta	EUR	Bu davlat yevrodan foydalanadi.	malta,мальта,mt
🇨🇾	Kipr	EUR	Bu davlat yevrodan foydalanadi.	cyprus,кипр,cy
🇭🇷	Xorvatiya	EUR	Bu davlat yevrodan foydalanadi.	croatia,хорватия,hr
🇧🇬	Bolgariya	EUR	Bu davlat yevrodan foydalanadi.	bulgaria,болгария,bg
🇦🇩	Andorra	EUR	Bu davlat yevrodan foydalanadi.	andorra,андорра,ad
🇲🇨	Monako	EUR	Bu davlat yevrodan foydalanadi.	monaco,монако,mc
🇸🇲	San-Marino	EUR	Bu davlat yevrodan foydalanadi.	san marino,сан марино,sm
🇻🇦	Vatikan	EUR	Bu davlat yevrodan foydalanadi.	vatican,ватикан,va
🇲🇪	Chernogoriya	EUR	Bu davlat yevrodan foydalanadi.	montenegro,черногория,me
🇽🇰	Kosovo	EUR	Bu davlat yevrodan foydalanadi.	kosovo,косово,xk
🇺🇸	Amerika Qo'shma Shtatlari	USD		usa,us,aqsh,amerika,america,united states,сша,америка,соединенные штаты,dollar,dollari,доллар
🇨🇦	Kanada	CAD		canada,канада,ca
🇲🇽	Meksika	MXN		mexico,мексика,mx
🇧🇷	Braziliya	BRL		brazil,бразилия,br
🇦🇷	Argentina	ARS		argentina,аргентина,ar
🇨🇱	Chili	CLP		chile,чили,cl
🇨🇴	Kolumbiya	COP		colombia,колумбия,co
🇵🇪	Peru	PEN		peru,перу,pe
🇻🇪	Venesuela	VES		venezuela,венесуэла,ve
🇪🇨	Ekvador	USD	Bu davlat AQSH dollaridan foydalanadi.	ecuador,эквадор,ec
🇧🇴	Boliviya	BOB		bolivia,боливия,bo
🇵🇾	Paragvay	PYG		paraguay,парагвай,py
🇺🇾	Urugvay	UYU		uruguay,уругвай,uy
🇬🇾	Gayana	GYD		guyana,гайана,gy
🇸🇷	Surinam	SRD		suriname,суринам,sr
🇵🇦	Panama	PAB		panama,панама,pa
🇨🇷	Kosta-Rika	CRC		costa rica,коста рика,cr
🇳🇮	Nikaragua	NIO		nicaragua,никарагуа,ni
🇭🇳	Gonduras	HNL		honduras,гондурас,hn
🇬🇹	Gvatemala	GTQ		guatemala,гватемала,gt
🇸🇻	Salvador	USD	Bu davlat AQSH dollaridan foydalanadi.	el salvador,сальвадор,sv
🇧🇿	Beliz	BZD		belize,белиз,bz
🇨🇺	Kuba	CUP		cuba,куба,cu
🇩🇴	Dominikana	DOP		dominican republic,доминикана,доминиканская республика,do
🇭🇹	Gaiti	HTG		haiti,гаити,ht
🇯🇲	Yamayka	JMD		jamaica,ямайка,jm
🇹🇹	Trinidad va Tobago	TTD		trinidad,trinidad and tobago,тринидад,tt
🇧🇸	Bagama orollari	BSD		bahamas,багамы,bs
🇧🇧	Barbados	BBD		barbados,барбадос,bb
🇦🇬	Antigua va Barbuda	XCD		antigua,антигуа,ag
🇩🇲	Dominika	XCD		dominica,доминика,dm
🇬🇩	Grenada	XCD		grenada,гренада,gd
🇰🇳	Sent-Kits va Nevis	XCD		saint kitts,сент китс,kn
🇱🇨	Sent-Lyusiya	XCD		saint lucia,сент люсия,lc
🇻🇨	Sent-Vinsent	XCD		saint vincent,сент винсент,vc
🇨🇳	Xitoy	CNY		china,китай,кнр,yuan,юань,cn
🇯🇵	Yaponiya	JPY		japan,япония,yen,iyen,иена,jp
🇰🇷	Janubiy Koreya	KRW		south korea,korea,koreya,южная корея,корея,kr
🇰🇵	Shimoliy Koreya	KPW		north korea,shimoliy koreya,северная корея,kp
🇲🇳	Mongoliya	MNT		mongolia,монголия,mn
🇮🇳	Hindiston	INR		india,индия,in
🇵🇰	Pokiston	PKR		pakistan,пакистан,pk
🇧🇩	Bangladesh	BDT		bangladesh,бангладеш,bd
🇱🇰	Shri-Lanka	LKR		sri lanka,шри ланка,lk
🇳🇵	Nepal	NPR		nepal,непал,np
🇧🇹	Butan	BTN		bhutan,бутан,bt
🇲🇻	Maldiv orollari	MVR		maldives,мальдивы,mv
🇦🇫	Afg'oniston	AFN		afghanistan,afgoniston,афганистан,af
🇮🇷	Eron	IRR		iran,иран,ir
🇮🇶	Iroq	IQD		iraq,ирак,iq
🇸🇾	Suriya	SYP		syria,сирия,sy
🇱🇧	Livan	LBP		lebanon,ливан,lb
🇯🇴	Iordaniya	JOD		jordan,иордания,jo
🇮🇱	Isroil	ILS		israel,израиль,il
🇵🇸	Falastin	ILS		palestine,палестина,ps
🇸🇦	Saudiya Arabistoni	SAR		saudi arabia,saudi,arabiston,саудовская аравия,саудия,sa
🇦🇪	Birlashgan Arab Amirliklari	AED		uae,emirates,baa,оаэ,эмираты,объединенные арабские эмираты,ae
🇶🇦	Qatar	QAR		qatar,катар,qa
🇰🇼	Quvayt	KWD		kuwait,кувейт,kw
🇧🇭	Bahrayn	BHD		bahrain,бахрейн,bh
🇴🇲	Ummon	OMR		oman,оман,om
🇾🇪	Yaman	YER		yemen,йемен,ye
🇮🇩	Indoneziya	IDR		indonesia,индонезия,id
🇲🇾	Malayziya	MYR		malaysia,малайзия,my
🇸🇬	Singapur	SGD		singapore,сингапур,sg
🇹🇭	Tailand	THB		thailand,таиланд,th
🇻🇳	Vetnam	VND		vietnam,вьетнам,vn
🇵🇭	Filippin	PHP		philippines,филиппины,ph
🇲🇲	Myanma	MMK		myanmar,burma,мьянма,бирма,mm
🇰🇭	Kambodja	KHR		cambodia,камбоджа,kh
🇱🇦	Laos	LAK		laos,лаос,la
🇧🇳	Bruney	BND		brunei,бруней,bn
🇹🇱	Sharqiy Timor	USD	Bu davlat AQSH dollaridan foydalanadi.	timor leste,timor,восточный тимор,tl
🇹🇼	Tayvan	TWD		taiwan,тайвань,tw
🇭🇰	Gonkong	HKD		hong kong,гонконг,hk
🇲🇴	Makao	MOP		macau,macao,макао,mo
🇪🇬	Misr	EGP		egypt,египет,eg
🇲🇦	Marokash	MAD		morocco,марокко,ma
🇩🇿	Jazoir	DZD		algeria,алжир,dz
🇹🇳	Tunis	TND		tunisia,тунис,tn
🇱🇾	Liviya	LYD		libya,ливия,ly
🇸🇩	Sudan	SDG		sudan,судан,sd
🇸🇸	Janubiy Sudan	SSP		south sudan,южный судан,ss
🇪🇹	Efiopiya	ETB		ethiopia,эфиопия,et
🇪🇷	Eritreya	ERN		eritrea,эритрея,er
🇸🇴	Somali	SOS		somalia,сомали,so
🇰🇪	Keniya	KES		kenya,кения,ke
🇹🇿	Tanzaniya	TZS		tanzania,танзания,tz
🇺🇬	Uganda	UGX		uganda,уганда,ug
🇷🇼	Ruanda	RWF		rwanda,руанда,rw
🇧🇮	Burundi	BIF		burundi,бурунди,bi
🇳🇬	Nigeriya	NGN		nigeria,нигерия,ng
🇬🇭	Gana	GHS		ghana,гана,gh
🇸🇳	Senegal	XOF		senegal,сенегал,sn
🇲🇱	Mali	XOF		mali,мали,ml
🇳🇪	Niger	XOF		niger,нигер,ne
🇧🇫	Burkina-Faso	XOF		burkina faso,burkina,буркина фасо,bf
🇨🇮	Kot-d'Ivuar	XOF		ivory coast,cote divoire,кот дивуар,ci
🇹🇬	Togo	XOF		togo,того,tg
🇧🇯	Benin	XOF		benin,бенин,bj
🇬🇼	Gvineya-Bisau	XOF		guinea bissau,гвинея бисау,gw
🇬🇳	Gvineya	GNF		guinea,гвинея,gn
🇱🇷	Liberiya	LRD		liberia,либерия,lr
🇸🇱	Sierra-Leone	SLE		sierra leone,сьерра леоне,sl
🇬🇲	Gambiya	GMD		gambia,гамбия,gm
🇨🇻	Kabo-Verde	CVE		cape verde,кабо верде,cv
🇨🇲	Kamerun	XAF		cameroon,камерун,cm
🇨🇫	Markaziy Afrika Respublikasi	XAF		central african republic,цар,центральноафриканская республика,cf
🇹🇩	Chad	XAF		chad,чад,td
🇨🇬	Kongo	XAF		congo,republic of the congo,конго,cg
🇨🇩	Kongo DR	CDF		kongo,dr congo,dr kongo,drc,kinshasa,конго,кдр,cd
🇬🇶	Ekvatorial Gvineya	XAF		equatorial guinea,экваториальная гвинея,gq
🇬🇦	Gabon	XAF		gabon,габон,ga
🇩🇯	Jibuti	DJF		djibouti,джибути,dj
🇰🇲	Komor orollari	KMF		comoros,коморы,km
🇲🇬	Madagaskar	MGA		madagascar,мадагаскар,mg
🇲🇺	Mavrikiy	MUR		mauritius,маврикий,mu
🇸🇨	Seyshel orollari	SCR		seychelles,сейшелы,sc
🇲🇼	Malavi	MWK		malawi,малави,mw
🇿🇲	Zambiya	ZMW		zambia,замбия,zm
🇿🇦	Janubiy Afrika	ZAR		south africa,юар,южная африка,za
🇳🇦	Namibiya	NAD		namibia,намибия,na
🇧🇼	Botsvana	BWP		botswana,ботсвана,bw
🇲🇿	Mozambik	MZN		mozambique,мозамбик,mz
🇦🇴	Angola	AOA		angola,ангола,ao
🇱🇸	Lesoto	LSL		lesotho,лесото,ls
🇸🇿	Esvatini	SZL		eswatini,swaziland,эсватини,свазиленд,sz
🇿🇼	Zimbabve	ZWG		zimbabwe,зимбабве,zw
🇲🇷	Mavritaniya	MRU		mauritania,мавритания,mr
🇸🇹	San-Tome va Prinsipi	STN		sao tome,сан томе,st
🇦🇺	Avstraliya	AUD		australia,австралия,au
🇳🇿	Yangi Zelandiya	NZD		new zealand,новая зеландия,nz
🇫🇯	Fiji	FJD		fiji,фиджи,fj
🇵🇬	Papua-Yangi Gvineya	PGK		papua new guinea,papua,папуа,pg
🇼🇸	Samoa	WST		samoa,самоа,ws
🇹🇴	Tonga	TOP		tonga,тонга,to
🇻🇺	Vanuatu	VUV		vanuatu,вануату,vu
🇸🇧	Solomon orollari	SBD		solomon islands,соломоновы острова,sb
🇰🇮	Kiribati	AUD	Bu davlat Avstraliya dollaridan foydalanadi.	kiribati,кирибати,ki
🇹🇻	Tuvalu	AUD	Bu davlat Avstraliya dollaridan foydalanadi.	tuvalu,тувалу,tv
🇵🇼	Palau	USD	Bu davlat AQSH dollaridan foydalanadi.	palau,палау,pw
🇫🇲	Mikroneziya	USD	Bu davlat AQSH dollaridan foydalanadi.	micronesia,микронезия,fm
🇲🇭	Marshall orollari	USD	Bu davlat AQSH dollaridan foydalanadi.	marshall islands,маршалловы острова,mh
🇳🇷	Nauru	AUD	Bu davlat Avstraliya dollaridan foydalanadi.	nauru,науру,nr
🇱🇮	Lixtenshteyn	CHF		liechtenstein,лихтенштейн,li
"""

PLACES = _rows(_PLACE_TEXT)


def normalize(text: str) -> str:
    value = text.strip().lower().replace("ё", "е")
    value = value.replace("ў", "у").replace("қ", "к").replace("ғ", "г").replace("ҳ", "х")
    for char in _APOSTROPHES:
        value = value.replace(char, "")
    value = value.replace(".", "")
    value = re.sub(r"[^0-9a-zа-я\s-]", " ", value)
    value = re.sub(r"[\s-]+", " ", value).strip()
    return value


_INDEX: dict[str, list[Place]] = {}
for _place in PLACES:
    for _label in (_place.name, *_place.aliases):
        _key = normalize(_label)
        if len(_key) < 2:
            continue
        _bucket = _INDEX.setdefault(_key, [])
        if _place not in _bucket:
            _bucket.append(_place)


def currency_place(code: str) -> Place:
    code = code.upper()
    return Place(
        _CODE_FLAGS.get(code, "💱"),
        CURRENCY_NAMES.get(code, code),
        code,
        (),
        "",
        "currency",
    )


def _unique(places: list[Place]) -> list[Place]:
    seen = []
    for place in places:
        if place not in seen:
            seen.append(place)
    return seen


def search(text: str) -> list[Place]:
    key = normalize(text)
    if not key or len(key) > 48:
        return []
    if re.fullmatch(r"[a-z]{3}", key) and key.upper() in CURRENCY_NAMES:
        return [currency_place(key.upper())]
    exact = _INDEX.get(key, [])
    if exact:
        return _unique(exact)
    if len(key) >= 4:
        prefixed = []
        for alias, places in _INDEX.items():
            if alias.startswith(key):
                prefixed.extend(places)
        prefixed = _unique(prefixed)
        if prefixed:
            return prefixed[:6]
    if len(key) >= 5:
        close = difflib.get_close_matches(key, list(_INDEX), n=6, cutoff=0.88)
        found = []
        for alias in close:
            found.extend(_INDEX[alias])
        return _unique(found)[:6]
    return []


def quotes_from_usd_table(table: dict, code: str) -> tuple[float, float] | None:
    if "UZS" not in table:
        return None
    uzs_per_usd = float(table["UZS"])
    if uzs_per_usd <= 0:
        return None
    if code == "USD":
        return uzs_per_usd, 1.0
    if code == "UZS":
        return 1.0, 1.0 / uzs_per_usd
    raw = table.get(code)
    if raw is None:
        return None
    units_per_usd = float(raw)
    if units_per_usd <= 0:
        return None
    return uzs_per_usd / units_per_usd, 1.0 / units_per_usd


def render_price(place: Place, per_uzs: float | None, per_usd: float | None, updated: str) -> str:
    code = place.currency
    currency_name = CURRENCY_NAMES.get(code, code)
    if place.kind == "currency":
        lines = [f"{place.flag} <b>{escape(code)}</b> — {escape(currency_name)}"]
    else:
        lines = [
            f"{place.flag} <b>{escape(place.name)}</b>",
            f"💱 <b>{escape(code)}</b> — {escape(currency_name)}",
        ]
    if place.note:
        lines.append(f"<i>{escape(place.note)}</i>")
    lines.append("")
    lines.append("📊 <b>Hozirgi narx</b>")
    if per_uzs is None or per_usd is None:
        lines.append("⏳ Hozirgi kurs manbada yo'q.")
    elif code == "UZS":
        lines.append(f"🇺🇸 1 <b>USD</b>  =  <b>{format_quote(1 / per_usd)} UZS</b>")
        lines.append(f"🇺🇿 1 <b>UZS</b>  =  <b>{format_quote(per_usd)} USD</b>")
    elif code == "USD":
        lines.append(f"🇺🇿 1 <b>USD</b>  =  <b>{format_quote(per_uzs)} UZS</b>")
    else:
        lines.append(f"🇺🇿 1 <b>{escape(code)}</b>  =  <b>{format_quote(per_uzs)} UZS</b>")
        lines.append(f"🇺🇸 1 <b>{escape(code)}</b>  =  <b>{format_quote(per_usd)} USD</b>")
    if updated and per_uzs is not None:
        lines.append(f"\n🕒 <i>Yangilangan:</i> {escape(updated)}")
    return "\n".join(lines)


def currency_flag(code: str) -> str:
    if code in _CODE_FLAGS:
        return _CODE_FLAGS[code]
    for place in PLACES:
        if place.currency == code:
            return place.flag
    return "💱"


def render_world_rates(table: dict, updated: str) -> list[str]:
    header = "🌍 <b>Butun dunyo — hozirgi narx</b>\nHar bir valyutaning 1 birligi necha so'm."
    if updated:
        header += f"\n🕒 <i>{escape(updated)}</i>"
    lines = []
    for code in sorted(table):
        if code == "UZS":
            continue
        pair = quotes_from_usd_table(table, code)
        if pair is None:
            continue
        per_uzs, _per_usd = pair
        name = CURRENCY_NAMES.get(code, code)
        lines.append(
            f"{currency_flag(code)} <b>{escape(code)}</b> · {escape(name)}\n"
            f"1 = <b>{format_quote(per_uzs)}</b> so'm"
        )
    if not lines:
        return [header + "\n\n⏳ Hozirgi kurslarni yig'ib bo'lmadi."]
    pages = []
    current = header
    for line in lines:
        piece = "\n\n" + line
        if len(current) + len(piece) > 3800:
            pages.append(current)
            current = "🌍 <b>Davom etadi</b>\n\n" + line
        else:
            current += piece
    pages.append(current)
    return pages


def render_choices(places: list[Place]) -> str:
    lines = ["🔎 <b>Bir nechta davlat topildi.</b>", "Aniqroq nom yozing:", ""]
    for place in places[:6]:
        currency_name = CURRENCY_NAMES.get(place.currency, place.currency)
        lines.append(f"{place.flag} <b>{escape(place.name)}</b> — {escape(currency_name)}")
    return "\n".join(lines)
