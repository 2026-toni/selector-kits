const SUPABASE_URL = "https://wuizpohykpvppmydfcng.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind1aXpwb2h5a3B2cHBteWRmY25nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyNDI1NDQsImV4cCI6MjA5MjgxODU0NH0.xFLEDRLmpvjR1oFZE9TetyT8706W_BQPr7vTrNR9sj8";

const MODEL_MAP = [
  [/EuroCargo\s*Tector\s*5\s*ML60E16\s*[/\s]?\s*ML65E16\s*[/\s]?\s*ML75E16\s*[/\s]?\s*ML80EL16\s*ML75E19\s*[/\s]?\s*ML80E19\s*[/\s]?\s*ML80EL19\s*[/\s]?\s*ML90E19\s*[/\s]?\s*ML100E19\s*[/\s]?\s*ML110EL19[/\s]?\s*ML120EL19\s*ML75E21\s*[/\s]?\s*ML80E21\s*[/\s]?\s*ML80EL21\s*[/\s]?\s*ML90E21\s*[/\s]?\s*ML100E21\s*[/\s]?\s*ML110EL21\s*[/\s]?\s*ML120EL21/i, "EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21"],
  [/FA\s*LF45\.180\s*[/\s]?\s*FA\s*LF55\.180\s*[/\s]?\s*FT\s*LF55\.180\s*[/\s]?\s*FAN\s*LF55\.180/i, "FA LF45.180 / FA LF55.180 / FT LF55.180 / FAN LF55.180"],
  [/Transit\s*Custom\s*2\.0\s*EURO\s*6AR\s*260\s*[/\s]?\s*280\s*[/\s]?\s*290\s*-\s*FWD\s*-AWD/i, "Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD"],
  [/HINO\s*SERIE\s*300\s*\(616[/\s]?617[/\s]?716[/\s]?717[/\s]?816[/\s]?817[/\s]?916[/\s]?917\)/i, "HINO SERIE 300 (616/617/716/717/816/817/916/917)"],
  [/eCanter\s*4,25\s*T\s*[/\s]?\s*6,0\s*T\s*[/\s]?\s*7,49\s*T\s*[/\s]?\s*8,55\s*T/i, "eCanter 4,25 T / 6,0 T / 7,49 T / 8,55 T"],
  [/FA\s*LF45\.220\s*[/\s]?\s*FA\s*LF55\.165\s*[/\s]?\s*FT\s*LF55\.220/i, "FA LF45.220 / FA LF55.165 / FT LF55.220"],
  [/P230\s*[/\s]?\s*P250\s*[/\s]?\s*P270\s*[/\s]?\s*P280\s*[/\s]?\s*P310\s*[/\s]?\s*P320/i, "P230 / P250 / P270 / P280 / P310 / P320"],
  [/EuroCargo\s*Tector\s*5\s*ML120E19\s*[/\s]?\s*ML140E19/i, "EuroCargo Tector 5 ML120E19 / ML140E19"],
  [/INTERSTAR\s*2\.3\s*dCi\s*-\s*FWD\s*\(EURO\s*6D\s*Full\)/i, "INTERSTAR 2.3 dCi - FWD (EURO 6D Full)"],
  [/INTERSTAR\s*2\.3\s*dCi\s*-\s*RWD\s*\(EURO\s*6D\s*Full\)/i, "INTERSTAR 2.3 dCi - RWD (EURO 6D Full)"],
  [/SERIE\s*-\s*N\s*Euro\s*5b\+\s*[/\s]?\s*Euro6\s*SÃ©rie\s*Bleu/i, "SERIE - N Euro 5b+ / Euro6 S\u00c3\u00a9rie Bleu"],
  [/TRANSIT\s*CUSTOM\s*2\.0\s*EcoBlue\s*Euro\s*6dtemp/i, "TRANSIT CUSTOM 2.0 EcoBlue Euro 6dtemp"],
  [/INTERSTAR\s*2\.0\s*dCi\s*-\s*FWD\s*\(EURO\s*6\.4\)/i, "INTERSTAR 2.0 dCi - FWD (EURO 6.4)"],
  [/INTERSTAR\s*2\.0\s*dCi\s*-\s*RWD\s*\(EURO\s*6\.4\)/i, "INTERSTAR 2.0 dCi - RWD (EURO 6.4)"],
  [/MOVANO\s*2\.3\s*CDTI\s*-\s*FWD\s*\(EURO\s*VI-D\)/i, "MOVANO 2.3 CDTI - FWD (EURO VI-D)"],
  [/GAZelle\s*Next\s*EA189\s*2\.0\s*TDI\s*-\s*RWD/i, "GAZelle Next EA189 2.0 TDI - RWD"],
  [/MASTER\s*2\.3\s*dCi\s*-\s*FWD\s*\(EURO\s*VI-D\)/i, "MASTER 2.3 dCi - FWD (EURO VI-D)"],
  [/R370\s*[/\s]?\s*R410\s*[/\s]?\s*R450\s*[/\s]?\s*R500\s*[/\s]?\s*R540/i, "R370 / R410 / R450 / R500 / R540"],
  [/COMBO\s*CARGO\s*2018\s*\(PSA\s*Platform\)/i, "COMBO CARGO 2018 (PSA Platform)"],
  [/MASTER\s*2\.0\s*dCi\s*-\s*FWD\s*\(EURO\s*6\.4\)/i, "MASTER 2.0 dCi - FWD (EURO 6.4)"],
  [/MASTER\s*2\.0\s*dCi\s*-\s*RWD\s*\(EURO\s*6\.4\)/i, "MASTER 2.0 dCi - RWD (EURO 6.4)"],
  [/MOVANO\s*2\.3\s*CDTI\s*-\s*FWD\s*\(EURO\s*6D\)/i, "MOVANO 2.3 CDTI - FWD (EURO 6D)"],
  [/MOVANO\s*2\.3\s*CDTI\s*-\s*RWD\s*\(EURO\s*6D\)/i, "MOVANO 2.3 CDTI - RWD (EURO 6D)"],
  [/NV400\s*2\.3\s*dCi\s*-\s*FWD\s*\(EURO\s*VI-D\)/i, "NV400 2.3 dCi - FWD (EURO VI-D)"],
  [/TRANSIT\s*2\.0\s*EcoBlue\s*Euro\s*6dtemp/i, "TRANSIT 2.0 EcoBlue Euro 6dtemp"],
  [/AXOR\s*1823\s*[/\s]?\s*1828\s*[/\s]?\s*2523\s*[/\s]?\s*2528/i, "AXOR 1823 / 1828 / 2523 / 2528"],
  [/LF45\.220\s*[/\s]?\s*LF45\.250\s*[/\s]?\s*LF55\.220/i, "LF45.220 / LF45.250 / LF55.220"],
  [/DYNA\s*L75\.34\s*[/\s]?\s*L75\.38\s*[/\s]?\s*L75\.42/i, "DYNA L75.34 / L75.38 / L75.42"],
  [/MASTER\s*2\.3\s*dCi\s*-\s*FWD\s*\(EURO6D\)/i, "MASTER 2.3 dCi - FWD (EURO6D)"],
  [/MASTER\s*2\.3\s*dCi\s*-\s*RWD\s*\(EURO6D\)/i, "MASTER 2.3 dCi - RWD (EURO6D)"],
  [/NV400\s*2\.3\s*dCi\s*-\s*FWD\s*\(EURO\s*6D\)/i, "NV400 2.3 dCi - FWD (EURO 6D)"],
  [/NV400\s*2\.3\s*dCi\s*-\s*RWD\s*\(EURO\s*6D\)/i, "NV400 2.3 dCi - RWD (EURO 6D)"],
  [/PROACE\s*MAX\s*2\.2\s*BlueHDi\s*MY2024/i, "PROACE MAX 2.2 BlueHDi MY2024"],
  [/TALENTO\s*1\.6\s*Multijet\s*[/\s]?\s*Ecojet/i, "TALENTO 1.6 Multijet / Ecojet"],
  [/XB230\s*[/\s]?\s*XB260\s*[/\s]?\s*XB290\s*[/\s]?\s*XB310/i, "XB230 / XB260 / XB290 / XB310"],
  [/300\s*Series\s*\(Euro\s*1\s*[/\s]?\s*Euro\s*2\)/i, "300 Series (Euro 1 / Euro 2)"],
  [/K320\s*[/\s]?\s*360\s*[/\s]?\s*410\s*[/\s]?\s*450\s*[/\s]?\s*490/i, "K320 / 360 / 410 / 450 / 490"],
  [/TRANSIT\s*[/\s]?\s*CUSTOM\s*2\.0\s*EcoBlue/i, "TRANSIT / CUSTOM 2.0 EcoBlue"],
  [/TRANSIT\s*CONNECT\s*2\.0\s*EcoBoost/i, "TRANSIT CONNECT 2.0 EcoBoost"],
  [/ELF\s*400\s*[/\s]?\s*ELF\s*500\s*[/\s]?\s*ELF\s*600/i, "ELF 400 / ELF 500 / ELF 600"],
  [/EXPRESS\s*VAN\s*1\.3\s*TCe\s*\(HR13\)/i, "EXPRESS VAN 1.3 TCe (HR13)"],
  [/TRANSIT\s*2\.0\s*Euro\s*6AR\s*[/\s]?\s*6EA/i, "TRANSIT 2.0 Euro 6AR / 6EA"],
  [/TRANSIT\s*2\.0\s*Euro\s*6EA\s*[/\s]?\s*6AR/i, "TRANSIT 2.0 Euro 6EA / 6AR"],
  [/TRANSIT\s*CUSTOM\s*2\.0\s*EcoBlue/i, "TRANSIT CUSTOM 2.0 EcoBlue"],
  [/FA\s*LF45\.140\s*[/\s]?\s*FA\s*LF45\.160/i, "FA LF45.140 / FA LF45.160"],
  [/JUMPER\s*2\.2\s*BlueHDi\s*MY2024/i, "JUMPER 2.2 BlueHDi MY2024"],
  [/MOVANO\s*2\.2\s*BlueHDi\s*MY2024/i, "MOVANO 2.2 BlueHDi MY2024"],
  [/BOXER\s*2\.2\s*BlueHDi\s*MY2024/i, "BOXER 2.2 BlueHDi MY2024"],
  [/RELAY\s*2\.2\s*BlueHDi\s*MY2024/i, "RELAY 2.2 BlueHDi MY2024"],
  [/SERIE\s*-\s*N\s*Euro\s*6D\s*[/\s]?\s*VI\s*E/i, "SERIE - N Euro 6D / VI E"],
  [/300\s*Series\s*\(EPA\s*TIER\s*3\)/i, "300 Series (EPA TIER 3)"],
  [/DAILY\s*3\.0\s*Natural\s*Power/i, "DAILY 3.0 Natural Power"],
  [/PROACE\s*CITY\s*1\.5\s*BlueHDi/i, "PROACE CITY 1.5 BlueHDi"],
  [/RANGER\s*2\.0\s*EcoBlue\s*TDCi/i, "RANGER 2.0 EcoBlue TDCi"],
  [/TOWNSTAR\s*1\.3\s*TCe\s*\(HR13\)/i, "TOWNSTAR 1.3 TCe (HR13)"],
  [/TRANSPORTER\s*T7\s*-\s*Euro\s*6/i, "TRANSPORTER T7 - Euro 6"],
  [/CITELIS12\s*[/\s]?\s*CITELIS\s*18/i, "CITELIS12 / CITELIS 18"],
  [/EuroCargo\s*Tector\s*6\s*CNG/i, "EuroCargo Tector 6 CNG"],
  [/EuroCargo\s*Tector\s*7\s*4X4/i, "EuroCargo Tector 7 4X4"],
  [/F-350XL\s*[/\s]?\s*FX350XL\s*PLUS/i, "F-350XL / FX350XL PLUS"],
  [/K230\s*[/\s]?\s*280\s*[/\s]?\s*320\s*[/\s]?\s*360/i, "K230 / 280 / 320 / 360"],
  [/K280\s*[/\s]?\s*320\s*[/\s]?\s*360\s*[/\s]?\s*370/i, "K280 / 320 / 360 / 370"],
  [/SERIE\s*-\s*N\s*Euro\s*6D\s*[/\s]?\s*VI/i, "SERIE - N Euro 6D / VI"],
  [/Econic\s*1827[/\s]?1830[/\s]?1835/i, "Econic 1827/1830/1835"],
  [/F-450\s*XL\s*\(SUPER\s*DUTY\)/i, "F-450 XL (SUPER DUTY)"],
  [/KANGOO\s*1\.3\s*TCe\s*\(HR13\)/i, "KANGOO 1.3 TCe (HR13)"],
  [/LF150\s*[/\s]?\s*LF180\s*[/\s]?\s*LF210/i, "LF150 / LF180 / LF210"],
  [/LF220\s*[/\s]?\s*LF250\s*[/\s]?\s*LF280/i, "LF220 / LF250 / LF280"],
  [/MOVANO\s*2\.3\s*CDTI\s*-\s*FWD/i, "MOVANO 2.3 CDTI - FWD"],
  [/MOVANO\s*2\.3\s*CDTI\s*-\s*RWD/i, "MOVANO 2.3 CDTI - RWD"],
  [/XB170\s*[/\s]?\s*XB190\s*[/\s]?\s*XB210/i, "XB170 / XB190 / XB210"],
  [/-\s*D\s*Wide\s*CAB\s*2\.3\s*m\s*-/i, "- D Wide CAB 2.3 m -"],
  [/EuroCargo\s*Tector\s*4X4/i, "EuroCargo Tector 4X4"],
  [/MASTER\s*2\.3\s*dCi\s*-\s*FWD/i, "MASTER 2.3 dCi - FWD"],
  [/MASTER\s*2\.3\s*dCi\s*-\s*RWD/i, "MASTER 2.3 dCi - RWD"],
  [/MASTER\s*3\.0\s*dCi\s*-\s*RWD/i, "MASTER 3.0 dCi - RWD"],
  [/300\s*Series\s*\(Euro\s*4\)/i, "300 Series (Euro 4)"],
  [/500\s*Series\s*\(Euro\s*2\)/i, "500 Series (Euro 2)"],
  [/DAILY\s*3\.0\s*HPI\s*-\s*HPT/i, "DAILY 3.0 HPI - HPT"],
  [/MAXUS\s*DELIVER\s*7\s*FWD/i, "MAXUS DELIVER 7 FWD"],
  [/MAXUS\s*DELIVER\s*9\s*FWD/i, "MAXUS DELIVER 9 FWD"],
  [/MAXUS\s*DELIVER\s*9\s*RWD/i, "MAXUS DELIVER 9 RWD"],
  [/NV400\s*2\.3\s*dCi\s*-\s*FWD/i, "NV400 2.3 dCi - FWD"],
  [/NV400\s*2\.3\s*dCi\s*-\s*RWD/i, "NV400 2.3 dCi - RWD"],
  [/TRAFIC\s*2\.0\s*Blue\s*dCi/i, "TRAFIC 2.0 Blue dCi"],
  [/TRANSIT\s*2\.0\s*EcoBlue/i, "TRANSIT 2.0 EcoBlue"],
  [/TRANSIT\s*CONNECT\s*1\.5/i, "TRANSIT CONNECT 1.5"],
  [/EXPERT\s*1\.5\s*BlueHDi/i, "EXPERT 1.5 BlueHDi"],
  [/EXPERT\s*2\.0\s*BlueHDi/i, "EXPERT 2.0 BlueHDi"],
  [/EXPERT\s*2\.2\s*BlueHDi/i, "EXPERT 2.2 BlueHDi"],
  [/EuroCargo\s*Tector\s*5/i, "EuroCargo Tector 5"],
  [/EuroCargo\s*Tector\s*7/i, "EuroCargo Tector 7"],
  [/MERCEDES\s*OC\s*500\s*RF/i, "MERCEDES OC 500 RF"],
  [/MOVANO\s*2\.2\s*BlueHDi/i, "MOVANO 2.2 BlueHDi"],
  [/P220\s*[/\s]?\s*P250\s*[/\s]?\s*P280/i, "P220 / P250 / P280"],
  [/P280\s*[/\s]?\s*P320\s*[/\s]?\s*P360/i, "P280 / P320 / P360"],
  [/PROACE\s*1\.5\s*BlueHDi/i, "PROACE 1.5 BlueHDi"],
  [/PROACE\s*2\.0\s*BlueHDi/i, "PROACE 2.0 BlueHDi"],
  [/PROACE\s*2\.2\s*BlueHDi/i, "PROACE 2.2 BlueHDi"],
  [/VIVARO\s*1\.5\s*BlueHDi/i, "VIVARO 1.5 BlueHDi"],
  [/VIVARO\s*2\.0\s*BlueHDi/i, "VIVARO 2.0 BlueHDi"],
  [/VIVARO\s*2\.2\s*BlueHDi/i, "VIVARO 2.2 BlueHDi"],
  [/AUMARK\s*7\.5[/\s]?8\.5\s*TN/i, "AUMARK 7.5/8.5 TN"],
  [/B13R[/\s]?RLE\s*-\s*EURO\s*6/i, "B13R/RLE - EURO 6"],
  [/CHASSIS\s*OC\s*500\s*RF/i, "CHASSIS OC 500 RF"],
  [/ELF\s*200\s*[/\s]?\s*ELF\s*300/i, "ELF 200 / ELF 300"],
  [/EURORIDER\s*397E\.12/i, "EURORIDER 397E.12"],
  [/JUMPY\s*1\.5\s*BlueHDi/i, "JUMPY 1.5 BlueHDi"],
  [/JUMPY\s*2\.0\s*BlueHDi/i, "JUMPY 2.0 BlueHDi"],
  [/JUMPY\s*2\.2\s*BlueHDi/i, "JUMPY 2.2 BlueHDi"],
  [/PRIMASTAR\s*2\.0\s*dCi/i, "PRIMASTAR 2.0 dCi"],
  [/SCUDO\s*1\.5\s*BlueHDi/i, "SCUDO 1.5 BlueHDi"],
  [/SCUDO\s*2\.0\s*BlueHDi/i, "SCUDO 2.0 BlueHDi"],
  [/SCUDO\s*2\.2\s*BlueHDi/i, "SCUDO 2.2 BlueHDi"],
  [/TGE\s*2\.0\s*TDI\s*-\s*FWD/i, "TGE 2.0 TDI - FWD"],
  [/TGE\s*2\.0\s*TDI\s*-\s*RWD/i, "TGE 2.0 TDI - RWD"],
  [/TORA\s*FSR\s*-\s*Euro\s*5/i, "TORA FSR - Euro 5"],
  [/DAILY\s*3\.0\s*MY2012/i, "DAILY 3.0 MY2012"],
  [/10\.190\s*[/\s]?\s*10\.220/i, "10.190 / 10.220"],
  [/CRAFTER\s*2\.0\s*TDI/i, "CRAFTER 2.0 TDI"],
  [/D-MAX\s*N57\s*[/\s]?\s*N60/i, "D-MAX N57 / N60"],
  [/EXPRESS\s*1\.6\s*dCi/i, "EXPRESS 1.6 dCi"],
  [/EXPRESS\s*2\.0\s*dCi/i, "EXPRESS 2.0 dCi"],
  [/EXPRESS\s*VAN\s*1\.5/i, "EXPRESS VAN 1.5"],
  [/SERIE\s*-\s*N\s*Euro6/i, "SERIE - N Euro6"],
  [/TALENTO\s*2\.0\s*dCi/i, "TALENTO 2.0 dCi"],
  [/TRANSIT\s*3\.7L\s*V6/i, "TRANSIT 3.7L V6"],
  [/HILUX\s*2\.4\s*D-4D/i, "HILUX 2.4 D-4D"],
  [/HILUX\s*2\.5\s*D-4D/i, "HILUX 2.5 D-4D"],
  [/NPR\s*85\s*[/\s]?\s*NKR85/i, "NPR 85 / NKR85"],
  [/PORTER\s*NP6\s*1\.5/i, "PORTER NP6 1.5"],
  [/SPRINTER\s*2\.143/i, "SPRINTER 2.143"],
  [/TRAFIC\s*1\.6\s*dCi/i, "TRAFIC 1.6 dCi"],
  [/TRAFIC\s*2\.0\s*dCi/i, "TRAFIC 2.0 dCi"],
  [/BERLINGO\s*2018/i, "BERLINGO 2018"],
  [/CITAN\s*110[/\s]?113/i, "CITAN 110/113"],
  [/FE\s*300\s*Hybrid/i, "FE 300 Hybrid"],
  [/NV250\s*1\.5\s*dCi/i, "NV250 1.5 dCi"],
  [/NV300\s*1\.6\s*dCi/i, "NV300 1.6 dCi"],
  [/NV300\s*2\.0\s*dCi/i, "NV300 2.0 dCi"],
  [/ProMaster\s*3\.0/i, "ProMaster 3.0"],
  [/B8R\s*\(Euro\s*5\)/i, "B8R (Euro 5)"],
  [/B8R\s*\(Euro\s*6\)/i, "B8R (Euro 6)"],
  [/PARTNER\s*2018/i, "PARTNER 2018"],
  [/SERIE-N\s*3,5t/i, "SERIE-N 3,5t"],
  [/SPRINTER\s*2\.0/i, "SPRINTER 2.0"],
  [/SPRINTER\s*3\.0/i, "SPRINTER 3.0"],
  [/VITO\s*1\.7\s*FWD/i, "VITO 1.7 FWD"],
  [/12\.250\s*FOCL/i, "12.250 FOCL"],
  [/FA\s*LF45\.130/i, "FA LF45.130"],
  [/FA\s*LF45\.140/i, "FA LF45.140"],
  [/PROACE\s*1\.5D/i, "PROACE 1.5D"],
  [/PROACE\s*1\.6D/i, "PROACE 1.6D"],
  [/PROACE\s*2\.0D/i, "PROACE 2.0D"],
  [/VIVARO\s*1\.5D/i, "VIVARO 1.5D"],
  [/VIVARO\s*2\.0D/i, "VIVARO 2.0D"],
  [/CADDY\s*2021/i, "CADDY 2021"],
  [/DOKKER\s*1\.5/i, "DOKKER 1.5"],
  [/DUCATO\s*3\.0/i, "DUCATO 3.0"],
  [/KANGOO\s*1\.5/i, "KANGOO 1.5"],
  [/C31\s*[/\s]?\s*C32/i, "C31 / C32"],
  [/CITAN\s*1\.5/i, "CITAN 1.5"],
  [/DAILY\s*2\.3/i, "DAILY 2.3"],
  [/DAILY\s*2\.8/i, "DAILY 2.8"],
  [/DAILY\s*3\.0/i, "DAILY 3.0"],
  [/H350\s*CRDi/i, "H350 CRDi"],
  [/MAXUS\s*V80/i, "MAXUS V80"],
  [/OPTARE\s*30/i, "OPTARE 30"],
  [/SCUDO\s*1\.5/i, "SCUDO 1.5"],
  [/SCUDO\s*2\.0/i, "SCUDO 2.0"],
  [/8\.5t\s*GVW/i, "8.5t GVW"],
  [/B11R\s*4x2/i, "B11R 4x2"],
  [/CF65\.220/i, "CF65.220"],
  [/CF75\.250/i, "CF75.250"],
  [/H-1\s*CRDi/i, "H-1 CRDi"],
  [/KW45\s*160/i, "KW45 160"],
  [/KW45\s*225/i, "KW45 225"],
  [/ELF\s*100/i, "ELF 100"],
  [/NKR\s*77L/i, "NKR 77L"],
  [/FE\s*250/i, "FE 250"],
  [/FL\s*210/i, "FL 210"],
  [/FL\s*240/i, "FL 240"],
  [/FL\s*250/i, "FL 250"],
  [/NPR\s*70/i, "NPR 70"],
  [/NPR\s*75/i, "NPR 75"],
  [/U-4000/i, "U-4000"],
  [/12240/i, "12240"],
  [/12250/i, "12250"],
  [/B7RLE/i, "B7RLE"],
  [/FL240/i, "FL240"],
  [/FRR90/i, "FRR90"],
  [/L-200/i, "L-200"],
  [/NP300/i, "NP300"],
  [/NT500/i, "NT500"],
  [/NV200/i, "NV200"],
  [/B11R/i, "B11R"],
  [/B12B/i, "B12B"],
  [/B13R/i, "B13R"],
  [/B9TL/i, "B9TL"],
  [/FL\s*6/i, "FL 6"],
  [/B9L/i, "B9L"],
  [/B9R/i, "B9R"],
  [/RC2/i, "RC2"],
  [/COMBO\s*CARGO\s*\(PSA\s*Platform\)/i, "COMBO CARGO (PSA Platform)"],
  [/SERIE\s*-\s*N\s*Euro\s*VI\s*OBD-D/i, "SERIE - N Euro VI OBD-D"],
  [/SERIE\s*-\s*N\s*Euro\s*VI\s*OBD-E/i, "SERIE - N Euro VI OBD-E"],
  [/ALEXANDER\s*DENNIS/i, "ALEXANDER DENNIS"],
  [/EuroCargo\s*Tector/i, "EuroCargo Tector"],
  [/AGORA\s*LINE\s*D\.D\./i, "AGORA LINE D.D."],
  [/TRANSIT\s*CONNECT/i, "TRANSIT CONNECT"],
  [/TRANSIT\s*COURIER/i, "TRANSIT COURIER"],
  [/TRANSIT\s*CUSTOM/i, "TRANSIT CUSTOM"],
  [/MASTER\s*-\s*FWD/i, "MASTER - FWD"],
  [/MASTER\s*-\s*RWD/i, "MASTER - RWD"],
  [/MOVANO\s*-\s*FWD/i, "MOVANO - FWD"],
  [/MOVANO\s*-\s*RWD/i, "MOVANO - RWD"],
  [/COMBO\s*CARGO/i, "COMBO CARGO"],
  [/DOBLO\s*CARGO/i, "DOBLO CARGO"],
  [/Double\s*Deck/i, "Double Deck"],
  [/N-Evolution/i, "N-Evolution"],
  [/TRANSPORTER/i, "TRANSPORTER"],
  [/DOKKER\s*VAN/i, "DOKKER VAN"],
  [/AvanCity\+/i, "AvanCity+"],
  [/EuroCargo/i, "EuroCargo"],
  [/INTERSTAR/i, "INTERSTAR"],
  [/LOGAN\s*VAN/i, "LOGAN VAN"],
  [/PRIMASTAR/i, "PRIMASTAR"],
  [/BERLINGO\\b/i, "BERLINGO"],
  [/EuroMidi/i, "EuroMidi"],
  [/KUBISTAR/i, "KUBISTAR"],
  [/SPRINTER\\b/i, "SPRINTER"],
  [/CABSTAR/i, "CABSTAR"],
  [/CRAFTER\\b/i, "CRAFTER"],
  [/FIORINO/i, "FIORINO"],
  [/INTOURO\\b/i, "INTOURO"],
  [/MASCOTT/i, "MASCOTT"],
  [/PARTNER\\b/i, "PARTNER"],
  [/SERIE\s*F/i, "SERIE F"],
  [/STRALIS\\b/i, "STRALIS"],
  [/Serie\s*K/i, "Serie K"],
  [/TGS[/\s]?TGX/i, "TGS/TGX"],
  [/TRANSIT\\b/i, "TRANSIT"],
  [/ACTROS\\b/i, "ACTROS"],
  [/ATLEON/i, "ATLEON"],
  [/BIPPER/i, "BIPPER"],
  [/CANTER\\b/i, "CANTER"],
  [/DOBLÃ“/i, "DOBL\u00c3\u201c"],
  [/DUCATO\\b/i, "DUCATO"],
  [/EXPERT\\b/i, "EXPERT"],
  [/JUMPER\\b/i, "JUMPER"],
  [/KANGOO\\b/i, "KANGOO"],
  [/MASTER\\b/i, "MASTER"],
  [/MAXITY/i, "MAXITY"],
  [/MIDLUM/i, "MIDLUM"],
  [/MOVANO\\b/i, "MOVANO"],
  [/PROACE\\b/i, "PROACE"],
  [/TRAFIC\\b/i, "TRAFIC"],
  [/VIVARO\\b/i, "VIVARO"],
  [/ANTOS/i, "ANTOS"],
  [/ATEGO\\b/i, "ATEGO"],
  [/BOXER\\b/i, "BOXER"],
  [/CADDY\\b/i, "CADDY"],
  [/CITAN/i, "CITAN"],
  [/COMBO\\b/i, "COMBO"],
  [/HIACE/i, "HIACE"],
  [/JUMPY\\b/i, "JUMPY"],
  [/MAXUS/i, "MAXUS"],
  [/S-WAY/i, "S-WAY"],
  [/SCUDO\\b/i, "SCUDO"],
  [/VARIO/i, "VARIO"],
  [/DYNA/i, "DYNA"],
  [/NEMO/i, "NEMO"],
  [/VITO\\b/i, "VITO"],
  [/TGA/i, "TGA"],
  [/TGL\\b/i, "TGL"],
  [/TGM\\b/i, "TGM"],
  [/TGS\\b/i, "TGS"],
  [/LT/i, "LT"]
];

const SYSTEM_PROMPT = `Eres un asistente comercial experto en selección de kits para vehículos.

ESTILO:
- Texto natural y conversacional. NUNCA uses ## o ### ni "PASO X".
- Conciso: máximo 3-4 líneas por respuesta salvo cuando muestres opciones.
- Confirma datos con "✓ [dato]" y pasa a la siguiente pregunta.
- Una sola pregunta por turno.

SELECCIÓN FINAL:
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor] · [vigente desde year_from_v4] · [componente] · [diferencial]
📋 Notas importantes: (muestra TODO el contenido de noteeng_clean — NO omitas nada: herramientas, restricciones, opciones de fábrica, referencias adicionales)
🔧 EMBRAGUE: el kit base incluye embrague_std de serie. Si embrague_esp tiene valor → ofrecer versión especial con sufijo según tipus_embrague: N=nada | N-E=[CODE]E (TM/UP/UNICLA) | N-S=[CODE]S (SANDEN) | N-E/S=ambos. Si tipus_embrague=N o vacío → no ofrecer nada aunque haya embrague_esp.

REGLAS:
- Solo recomiendas códigos que existan en los datos recibidos.
- No inventas datos. Una pregunta por turno.
- Excluye STANDARD BRACKET y COMPRESSOR BRACKET.
- Cuando identifiques un motor en engine_all (separados por |), todos son válidos para ese kit.
- NUNCA digas que un componente no existe si aparece en la lista de componentes disponibles.

FLUJO (detente al llegar a 1 código único):

1. TIPO DE KIT — siempre primera:
   KB=compresor A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis

2. MARCA — campo brand.
   💡 Permiso circulación campo D.1

3. MODELO — muestra opciones reales de model_clean (4-8 ejemplos).
   💡 Permiso campos D.2 y D.3

4. TRACCIÓN — inmediatamente tras confirmar modelo, si hay variantes RWD/FWD en los datos:
   "¿Tracción trasera (RWD) o delantera (FWD)?"
   Si solo hay una opción de tracción, omite.

5. ¿VEHÍCULO NUEVO? — tras modelo y tracción:
   "¿Es un vehículo de matriculación reciente?"
   SÍ = usa kits con year_to_int NULO (vigentes).
   NO = pide año exacto.

6. AÑO — solo si no dijo nuevo:
   "¿Año de fabricación o primera matriculación?"
   💡 Permiso campo B

7. MOTOR — si quedan varios. Usa engine_all (contiene todos los motores separados por |).
   💡 Permiso campo P.5 o etiqueta tapa válvulas

8. COMPONENTE — agrupa por tipo. Muestra opciones reales de nom_opcio_compressor.
   Abreviaciones: TM15=TM 15/QP 15, TM13=TM 13/QP 13, etc.

9. FLAGS KIT (solo si varían entre candidatos):
   flag_gearbox_v3: ok=auto OK, not=NO auto, vacío=ambas → NO preguntar si todos vacíos
   flag_auto_tensioner → tensor auto vs estándar
   flag_pfmot_yes/no → PTO/PFMot
   flag_urban_kit → entorno urbano
   flag_ind_belt → correa independiente
   flag_n63_pulley_yes/no + flag_n63_full_option → polea N62/N63
   flag_sanden → compresor SANDEN

10. A/C — solo si ac_filter mezcla yes/no: "¿Tiene A/C de fábrica?"
    ac_filter=any → NO preguntar.`;

function detectModel(text) {
  for (const [re, model] of MODEL_MAP) {
    if (re.test(text)) return model;
  }
  return null;
}

function normalizeComponent(text) {
  const compMap = [
    [/TM\s*43/i, 'TM 43'],
    [/TM\s*31/i, 'TM 31 / QP 31'],
    [/TM\s*21/i, 'TM 21 / QP 21'],
    [/TM\s*16/i, 'TM 16 / QP 16'],
    [/TM\s*15/i, 'TM 15 / QP 15'],
    [/TM\s*13/i, 'TM 13 / QP 13'],
    [/TM\s*08|TM\s*8\b/i, 'TM 08 / QP 08'],
    [/QP\s*25/i, 'QP 25'],
    [/UP\s*170|UPF\s*170/i, 'UP 170 / UPF 170'],
    [/UP\s*150|UPF\s*150/i, 'UP 150 / UPF 150'],
    [/UP\s*120|UPF\s*120/i, 'UP 120 / UPF 120'],
    [/UPF\s*200/i, 'UPF 200'],
    [/UP\s*90/i, 'UP 90'],
    [/SD7H15/i, 'SD7H15'],
    [/SD7L15/i, 'SD7L15'],
    [/SD5H14/i, 'SD5H14'],
    [/SD5L14/i, 'SD5L14'],
    [/SD5H09/i, 'SD5H09'],
    [/CS\s*150/i, 'CS150'],
    [/CS\s*90/i, 'CS90'],
    [/CS\s*55/i, 'CS55'],
    [/CR\s*2323/i, 'CR2323'],
    [/CR\s*2318/i, 'CR2318'],
    [/CR\s*150/i, 'CR150'],
    [/CR\s*90/i, 'CR90'],
    [/SALAMI.*16|16.*SALAMI|16\s*cc/i, '16 cc SALAMI'],
    [/SALAMI.*12|12.*SALAMI|12\s*cc/i, '12 cc SALAMI'],
    [/SALAMI.*8|8.*SALAMI|8\s*cc/i, '8 cc SALAMI'],
    [/MG\s*29|Mahle.*200A|200A.*14V/i, 'Mahle MG 29 (200A 14V)'],
    [/MG\s*142|Mahle.*100A|100A.*28V/i, 'Mahle MG 142 (100A 28V)'],
    [/Valeo|140A\s*14V/i, 'Valeo 140A 14V'],
    [/SEG|150A\s*28V/i, 'SEG 150A 28V'],
    [/G4.*400|400V.*G4/i, 'Generator "G4-400V"'],
    [/G4.*230|230V.*G4/i, 'Generator "G4-230V"'],
    [/G3.*400|400V.*G3/i, 'Generator "G3-400V"'],
    [/G3.*230|230V.*G3/i, 'Generator "G3-230V"'],
    [/TK.?315/i, 'TK-315'],
    [/TK.?312/i, 'TK-312'],
    [/BITZER/i, 'BITZER 4UFC'],
    [/BOCK/i, 'BOCK FK40'],
    [/Xarios/i, 'Xarios Integrated'],
    [/BOCK/i, 'BOCK FK40'],
    [/ELH7/i, 'ELH7'],
    [/HGX34P/i, 'HGX34P'],
    [/HG34P/i, 'HG34P'],
    [/HPI\s*15/i, 'HPI 15cc'],
    [/HPI\s*12/i, 'HPI 12cc'],
    [/HPI\s*8/i, 'HPI 8cc'],
    [/IPH\s*25/i, 'IPH 25cc'],
    [/X.?430/i, 'X-430'],
  ];
  for (const [re, name] of compMap) {
    if (re.test(text)) return name;
  }
  return null;
}

function extractState(messages) {
  const text = messages.map(m => typeof m.content === 'string' ? m.content : '').join(' ');
  const s = {};

  // Kit type
  if (/compresor\s*a\/c|\bkb\b/i.test(text)) s.kit_type = 'Kit compresor A/C';
  else if (/fr[ií]o\s*industrial|\bkc\b/i.test(text)) s.kit_type = 'Kit compresor frío industrial';
  else if (/alternador|\bka\b/i.test(text)) s.kit_type = 'Kit alternador';
  else if (/bomba\s*hidráulica|\bkh\b/i.test(text)) s.kit_type = 'Kit bomba hidráulica';
  else if (/generador|\bkg\b/i.test(text)) s.kit_type = 'Kit generador';
  else if (/chasis|\bkf\b/i.test(text)) s.kit_type = 'Kit chasis';

  // Brand
  const brandMap = [
    [/sprinter|vito|actros|atego|arocs|antos|axor|econic/i, 'MERCEDES'],
    [/ducato|scudo|talento|doblo/i, 'FIAT'],
    [/transit|tourneo/i, 'FORD'],
    [/\bmaster\b|trafic|kangoo/i, 'RENAULT'],
    [/\bdaily\b|eurocargo|stralis|trakker/i, 'IVECO'],
    [/\bboxer\b|expert|partner/i, 'PEUGEOT'],
    [/jumper|jumpy|berlingo/i, 'CITROEN'],
    [/crafter|transporter/i, 'VW'],
    [/movano|vivaro|\bcombo\b/i, 'OPEL'],
    [/nv400|nv300|interstar|primastar/i, 'NISSAN'],
    [/\btgl\b|\btgm\b|\btgs\b|\btgx\b/i, 'MAN'],
    [/canter|fuso/i, 'MITSUBISHI'],
    [/\bvolvo\b/i, 'VOLVO'],
    [/\bdaf\b/i, 'DAF'],
  ];
  for (const [re, brand] of brandMap) {
    if (re.test(text)) { s.brand = brand; break; }
  }
  for (const b of ['RENAULT','FIAT','IVECO','FORD','MERCEDES','VW','OPEL','NISSAN','PEUGEOT','CITROEN','MAN','DAF','VOLVO','TOYOTA','MITSUBISHI']) {
    if (new RegExp('\\b'+b+'\\b','i').test(text)) { s.brand = b; break; }
  }

  // Model - detect from conversation using MODEL_MAP
  const detectedModel = detectModel(text);
  if (detectedModel && detectedModel !== 'SPRINTER' && detectedModel !== 'TRANSIT' && 
      detectedModel !== 'DUCATO' && detectedModel !== 'MASTER') {
    s.model_clean = detectedModel;
  } else if (detectedModel) {
    s.model_clean = detectedModel;
  }

  // Traction
  if (/\brwd\b|tracci[oó]n\s*trasera|rear\s*wheel/i.test(text)) s.flag_rwd = true;
  if (/\bfwd\b|tracci[oó]n\s*delantera|front\s*wheel/i.test(text)) s.flag_fwd = true;

  // New vehicle
  if (/nuevo|reciente|nueva\s*matriculaci|es\s*nuevo|si.*nuevo/i.test(text)) s.new_vehicle = true;

  // Year
  if (!s.new_vehicle) {
    const ym = text.match(/\b(19[89]\d|20[012]\d)\b/);
    if (ym) s.year = parseInt(ym[1]);
  }

  // Component
  s.component = normalizeComponent(text);

  return s;
}

async function queryDB(s) {
  const parts = [
    'brand=neq.ACCESSORY',
    'kit_type=neq.Otro',
    'model_clean=neq.STANDARD%20BRACKET',
    'model_clean=neq.COMPRESSOR%20BRACKET',
    'limit=200',
  ];

  if (s.kit_type) parts.push(`kit_type=eq.${encodeURIComponent(s.kit_type)}`);
  if (s.brand) parts.push(`brand=eq.${encodeURIComponent(s.brand)}`);
  if (s.model_clean) parts.push(`model_clean=eq.${encodeURIComponent(s.model_clean)}`);
  if (s.flag_rwd) parts.push('flag_rwd=eq.Yes');
  if (s.flag_fwd) parts.push('flag_fwd=eq.Yes');

  if (s.new_vehicle) {
    parts.push('year_to_int=is.null');
  } else if (s.year) {
    parts.push(`year_from_int=lte.${s.year}`);
    parts.push(`or=(year_to_int.is.null,year_to_int.gte.${s.year})`);
  }

  if (s.component) {
    parts.push(`nom_opcio_compressor=eq.${encodeURIComponent(s.component)}`);
  }

  const url = `${SUPABASE_URL}/rest/v1/kits?${parts.join('&')}`;
  const r = await fetch(url, {
    headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
  });
  if (!r.ok) throw new Error(`DB ${r.status}`);
  return r.json();
}

function buildContext(data, state) {
  if (!data || data.length === 0) return '[BD: Sin resultados]';

  const byCode = {};
  for (const row of data) {
    if (!byCode[row.code]) byCode[row.code] = row;
  }
  const codes = Object.values(byCode);
  const uniq = arr => [...new Set(arr.filter(Boolean))];

  const summary = {
    total_codes: codes.length,
    models: uniq(codes.map(r => r.model_clean)),
    engines: uniq(codes.map(r => r.engine_all || r.engine_clean)),
    components: uniq(data.map(r => r.nom_opcio_compressor)),
    tractions: { rwd: codes.filter(r=>r.flag_rwd==='Yes').length, fwd: codes.filter(r=>r.flag_fwd==='Yes').length },
    filters_active: state,
  };

  if (codes.length <= 10) {
    const detail = codes.map(r => ({
      code: r.code,
      model: r.model_clean,
      engine: r.engine_all || r.engine_clean,
      year_from_v4: r.year_from_v4,
      year_to_v4: r.year_to_v4 || null,
      components: uniq(data.filter(d=>d.code===r.code).map(d=>d.nom_opcio_compressor)),
      flag_rwd: r.flag_rwd||null, flag_fwd: r.flag_fwd||null, flag_awd: r.flag_awd||null,
      flag_auto_tensioner: r.flag_auto_tensioner||null,
      flag_n63_pulley_yes: r.flag_n63_pulley_yes||null,
      flag_n63_pulley_no: r.flag_n63_pulley_no||null,
      flag_n63_full_option: r.flag_n63_full_option||null,
      flag_pfmot_yes: r.flag_pfmot_yes||null, flag_pfmot_no: r.flag_pfmot_no||null,
      flag_urban_kit: r.flag_urban_kit||null, flag_ind_belt: r.flag_ind_belt||null,
      flag_sanden: r.flag_sanden||null, flag_gearbox_v3: r.flag_gearbox_v3||null,
      flag_himatic: r.flag_himatic||null, flag_not_18t: r.flag_not_18t||null,
      ac_filter: r.ac_filter||null,
      noteeng: r.noteeng_clean||r.noteeng||null,
      embrague_esp: r.embrague_esp||null,
      embrague_std: r.embrague_std||null,
      tipus_embrague: r.tipus_embrague||null,
    }));
    return `[BD ${codes.length} códigos]\n[Resumen: ${JSON.stringify(summary)}]\n[Detalle: ${JSON.stringify(detail)}]`;
  }

  return `[BD ${codes.length} códigos - demasiados para mostrar detalle]\n[Resumen: ${JSON.stringify(summary)}]`;
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };
  const API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!API_KEY) return { statusCode: 500, body: JSON.stringify({ error: 'API key no configurada' }) };

  try {
    const body = JSON.parse(event.body);
    const messages = body.messages || [];
    const state = extractState(messages);

    let ctx = '[BD: Sin datos]';
    try {
      const data = await queryDB(state);
      ctx = buildContext(data, state);
    } catch(e) {
      ctx = `[BD Error: ${e.message}]`;
    }

    const msgsWithCtx = [...messages];
    const last = msgsWithCtx[msgsWithCtx.length - 1];
    msgsWithCtx[msgsWithCtx.length - 1] = {
      ...last,
      content: (typeof last.content === 'string' ? last.content : '') + '\n\n' + ctx
    };

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 800,
        system: SYSTEM_PROMPT,
        messages: msgsWithCtx
      })
    });

    const data = await resp.json();
    if (!resp.ok) return { statusCode: resp.status, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: data.error?.message }) };
    return { statusCode: 200, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) };

  } catch(err) {
    return { statusCode: 500, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: err.message }) };
  }
};
