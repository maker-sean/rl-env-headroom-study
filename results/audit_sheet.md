# Hand-audit sheet: 20 CORD v2 test receipts

git `374bd1f-DIRTY` | seed 20261106 | split `test` | 20 of 100 documents

Columns are: the raw string CORD annotates, and the integer this repo parsed it into. The audit question for each row is whether that integer is the amount the receipt actually prints.

The second audit question is the annotation ceiling: count the item lines the page text prints and compare that to `items annotated`. Where the page prints more, exact match is capped below 1.0 for that document no matter what a model outputs.

Page images are in `results/audit/`.

| # | doc | items annotated | scalars | verdict (fill in) |
|---|---|---|---|---|
| 1 | [test-013](#test-013) | 2 | 3 | |
| 2 | [test-099](#test-099) | 1 | 4 | |
| 3 | [test-047](#test-047) | 3 | 2 | |
| 4 | [test-067](#test-067) | 1 | 1 | |
| 5 | [test-000](#test-000) | 1 | 4 | |
| 6 | [test-001](#test-001) | 3 | 1 | |
| 7 | [test-003](#test-003) | 1 | 2 | |
| 8 | [test-006](#test-006) | 3 | 1 | |
| 9 | [test-011](#test-011) | 1 | 1 | |
| 10 | [test-015](#test-015) | 2 | 1 | |
| 11 | [test-018](#test-018) | 1 | 1 | |
| 12 | [test-028](#test-028) | 3 | 5 | |
| 13 | [test-031](#test-031) | 2 | 4 | |
| 14 | [test-035](#test-035) | 4 | 1 | |
| 15 | [test-036](#test-036) | 1 | 2 | |
| 16 | [test-042](#test-042) | 1 | 3 | |
| 17 | [test-053](#test-053) | 3 | 4 | |
| 18 | [test-082](#test-082) | 3 | 2 | |
| 19 | [test-086](#test-086) | 2 | 2 | |
| 20 | [test-088](#test-088) | 2 | 2 | |

## test-013

**Touched by a bug fix.** Check this one first.

### Page text, as the model saw it

```
BASO KUAH 1 43.636 43.636
A.MINERAL GELAS 1 3,000 3,000
TOTAL 46.636
DPP 46.636
TAX 10.00 % 4.664
GRAND TOTAL 51.300
TUNAI 52.000
KEMBALI 700
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `["46.636", "46.636"]` **(list)** | 46636 | |
| tax | `"4.664"` | 4664 | |
| total | `"51.300"` | 51300 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"BASO KUAH"` | `"43.636"` | `"43.636"` | BASO KUAH | 43636 | 43636 | 1.0 | |
| 2 | `"A.MINERAL GELAS"` | `"3,000"` | `"3,000"` | A.MINERAL GELAS | 3000 | 3000 | 1.0 | |

![test-013](audit/test-013.png)

---

## test-099

**Touched by a bug fix.** Check this one first.

### Page text, as the model saw it

```
1 FL-Xmas 30 Off 68,180
1 PAKET SLICES 0
1 FL Cake - French 0
Vanilla SLC
1 PAKET SLICES 0
1 FL Cake - Green 0
Tea SLC
1 PAKET SLICES 0
1 FL Cake - Belgium 0
Choco SLC
SUBTOTAL 68,180
DISKON 0
BIAYA TAMBAHAN 0
PAJAK PPN 10 % 6,818
PAJAK 0% 0
BIAYA CC 0
PEMBULATAN 2
TOTAL 75,000
TUNAI 0
NON TUNAI 75,000
KEMBALI 0
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"68,180"` | 68180 | |
| tax | `["6,818", "0"]` **(list)** | 6818 | |
| discount | `"0"` | 0 | |
| total | `"75,000"` | 75000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"FL-Xmas 30 Off"` | `null` | `"68,180"` | FL-Xmas 30 Off | None | 68180 | 1.0 | |

![test-099](audit/test-099.png)

---

## test-047

**Touched by a bug fix.** Check this one first.

### Page text, as the model saw it

```
COPIA 1 /GB 1 45,000.00
2100252000358 45,000.00
PLASTIC BAG RED CENTRAL SI 1 0.00
9100544260074 0.00
COPIA 1 /GB 1 18,000.00
2100252000358 18,000.00
Total 63,000.00
Total discount 0.00
Total quantity 3
Card Payment DEBIT CARD
63,000.00
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| discount | `"0.00"` | 0 | |
| total | `"63,000.00"` | 63000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"COPIA 1 /GB"` | `"45,000.00"` | `"45,000.00"` | COPIA 1 /GB | 45000 | 45000 | 1.0 | |
| 2 | `"PLASTIC BAG RED CENTRAL SI"` | `"0.00"` | `"0.00"` | PLASTIC BAG RED CENTRAL SI | 0 | 0 | 1.0 | |
| 3 | `"COPIA 1 /GB"` | `"18,000.00"` | `"18,000.00"` | COPIA 1 /GB | 18000 | 18000 | 1.0 | |

![test-047](audit/test-047.png)

---

## test-067

**Touched by a bug fix.** Check this one first.

### Page text, as the model saw it

```
2005- CHEESE JOHN
9.500,00 x1 9.500,00
Total Item: 1
Total. 9.500,00
Cash
Tendered: 9.500,00
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"9.500,00"` | 9500 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"CHEESE JOHN"` | `"9.500,00"` | `"9.500,00"` | CHEESE JOHN | 9500 | 9500 | 1.0 | |

![test-067](audit/test-067.png)

---

## test-000

### Page text, as the model saw it

```
901016 -TICKET CP
2 60.000 60.000
TOTAL DISC $ -60.000
TAX 5.455
Subtotal 60.000
TOTAL (Qty 2.00 60.000
EDC CIMB NIAGA No: xx7730 60.000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"60.000"` | 60000 | |
| tax | `"5.455"` | 5455 | |
| discount | `"-60.000"` | -60000 | |
| total | `"60.000"` | 60000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"-TICKET CP"` | `null` | `"60.000"` | -TICKET CP | None | 60000 | 2.0 | |

![test-000](audit/test-000.png)

---

## test-001

### Page text, as the model saw it

```
J.STB PROMO 17500
Y.B.BAT 46000
Y.BASO PROM 27500
TOTAL 91000
CASH 91000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"91000"` | 91000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"J.STB PROMO"` | `null` | `"17500"` | J.STB PROMO | None | 17500 | None | |
| 2 | `"Y.B.BAT"` | `null` | `"46000"` | Y.B.BAT | None | 46000 | None | |
| 3 | `"Y.BASO PROM"` | `null` | `"27500"` | Y.BASO PROM | None | 27500 | None | |

![test-001](audit/test-001.png)

---

## test-003

### Page text, as the model saw it

```
1X @11000
DONAT GULA 11,000
1.00xITEMs
SUBTOTAL 11,000
TOTAL 11,000
CASH 11,000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"11,000"` | 11000 | |
| total | `"11,000"` | 11000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"DONAT GULA"` | `"@11000"` | `"11,000"` | DONAT GULA | 11000 | 11000 | 1.0 | |

![test-003](audit/test-003.png)

---

## test-006

### Page text, as the model saw it

```
1 EGG TART 13,000
2 CHOCO CUS ARD PASTRY 24,000
1 REDBEAN BREAD 9,000
TOTAL 46,000
CASH 50,000
CHANGE 4,000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"46,000"` | 46000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"EGG TART"` | `null` | `"13,000"` | EGG TART | None | 13000 | 1.0 | |
| 2 | `"CHOCO CUS ARD PASTRY"` | `null` | `"24,000"` | CHOCO CUS ARD PASTRY | None | 24000 | 2.0 | |
| 3 | `"REDBEAN BREAD"` | `null` | `"9,000"` | REDBEAN BREAD | None | 9000 | 1.0 | |

![test-006](audit/test-006.png)

---

## test-011

### Page text, as the model saw it

```
1 BANABERRY FRESH CREAM CAK 230,000
TOTAL CASH 230,000 230,000
CHANGE 0
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"230,000"` | 230000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"BANABERRY FRESH CREAM CAK"` | `null` | `"230,000"` | BANABERRY FRESH CREAM CAK | None | 230000 | 1.0 | |

![test-011](audit/test-011.png)

---

## test-015

### Page text, as the model saw it

```
1 Lemon Tea (L) 25.000
1 Caramel Small 38.000
TOTAL 63.000
CASH 70.000
CHANGED 7.000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"63.000"` | 63000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Lemon Tea (L)"` | `null` | `"25.000"` | Lemon Tea (L) | None | 25000 | 1.0 | |
| 2 | `"Caramel Small"` | `null` | `"38.000"` | Caramel Small | None | 38000 | 1.0 | |

![test-015](audit/test-015.png)

---

## test-018

### Page text, as the model saw it

```
Propolis Cair 1
156000
156000
Sub Tofal
156000
Tunai
156000
Kembalian Rp. 0
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"156000"` | 156000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Propolis Cair"` | `"156000"` | `"156000"` | Propolis Cair | 156000 | 156000 | 1.0 | |

![test-018](audit/test-018.png)

---

## test-028

### Page text, as the model saw it

```
SAMGYOPSAL 2 194,000
SUL LUNG TANG 1 75,000
MAKOLI 1 100,000
Sub Total 369,000
Service 18,450
VAT 38,745
Discount 0
TOTAL 426,195
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"369,000"` | 369000 | |
| tax | `"38,745"` | 38745 | |
| service_charge | `"18,450"` | 18450 | |
| discount | `"0"` | 0 | |
| total | `"426,195"` | 426195 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"SAMGYOPSAL"` | `null` | `"194,000"` | SAMGYOPSAL | None | 194000 | 2.0 | |
| 2 | `"SUL LUNG TANG"` | `null` | `"75,000"` | SUL LUNG TANG | None | 75000 | 1.0 | |
| 3 | `"MAKOLI"` | `null` | `"100,000"` | MAKOLI | None | 100000 | 1.0 | |

![test-028](audit/test-028.png)

---

## test-031

### Page text, as the model saw it

```
1 SALMON PESTO 85,500
1 SALMON PESTO 85,500
Disc -100% (ITM06) -85,500
SUBTTL 85,500
SVC CHG 6% 10,260
PB1 10% 18,126
TOTAL 113,886
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"85,500"` | 85500 | |
| tax | `"18,126"` | 18126 | |
| service_charge | `"10,260"` | 10260 | |
| total | `"113,886"` | 113886 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"SALMON PESTO"` | `null` | `"85,500"` | SALMON PESTO | None | 85500 | 1.0 | |
| 2 | `"SALMON PESTO"` | `null` | `"85,500"` | SALMON PESTO | None | 85500 | 1.0 | |

![test-031](audit/test-031.png)

---

## test-035

### Page text, as the model saw it

```
2 TWIST DONUT 18,000
1 BANANA DONUT 11,000
1 CREAMCHEESE BREAD 13,000
1 FRANKFRUT SAUSAGE ROLL 12,000
TOTAL 54,000
CASH 104,000
CHANGE 50,000
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| total | `"54,000"` | 54000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"TWIST DONUT"` | `null` | `"18,000"` | TWIST DONUT | None | 18000 | 2.0 | |
| 2 | `"BANANA DONUT"` | `null` | `"11,000"` | BANANA DONUT | None | 11000 | 1.0 | |
| 3 | `"CREAMCHEESE BREAD"` | `null` | `"13,000"` | CREAMCHEESE BREAD | None | 13000 | 1.0 | |
| 4 | `"FRANKFRUT SAUSAGE ROLL"` | `null` | `"12,000"` | FRANKFRUT SAUSAGE ROLL | None | 12000 | 1.0 | |

![test-035](audit/test-035.png)

---

## test-036

### Page text, as the model saw it

```
1 XXL Crispy Chicken 40,000
1 - Sedang 0
ITEMS: 1 40,000
Total 40,000
Cash 100,000 Change : 60,000
Pay
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"40,000"` | 40000 | |
| total | `"40,000"` | 40000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"XXL Crispy Chicken"` | `null` | `"40,000"` | XXL Crispy Chicken | None | 40000 | 1.0 | |

![test-036](audit/test-036.png)

---

## test-042

### Page text, as the model saw it

```
1 Chicken HCC. 1Pcs 15.000
Sub Total 15,000
P.Rest 10 % 1,500
Total 16,500
Cash 50,000
Kembali 33,500
1 Items,
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"15,000"` | 15000 | |
| tax | `"1,500"` | 1500 | |
| total | `"16,500"` | 16500 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Chicken HCC. 1Pcs"` | `null` | `"15.000"` | Chicken HCC. 1Pcs | None | 15000 | 1.0 | |

![test-042](audit/test-042.png)

---

## test-053

### Page text, as the model saw it

```
1 Pecel Komplit + Nasi 42.000
1 SOTO KUDUS 47.000
2 Mineral Water 18.000
Subtotal 107.000
Servi Charge 57 5.350
Pajak Rest 10% 11.235
4 Total 123.585
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"107.000"` | 107000 | |
| tax | `"11.235"` | 11235 | |
| service_charge | `"5.350"` | 5350 | |
| total | `"123.585"` | 123585 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Pecel Komplit + Nasi"` | `null` | `"42.000"` | Pecel Komplit + Nasi | None | 42000 | 1.0 | |
| 2 | `"SOTO KUDUS"` | `null` | `"47.000"` | SOTO KUDUS | None | 47000 | 1.0 | |
| 3 | `"Mineral Water"` | `null` | `"18.000"` | Mineral Water | None | 18000 | 2.0 | |

![test-053](audit/test-053.png)

---

## test-082

### Page text, as the model saw it

```
Chocolate Log Cake 1x 115,000 115,000
Snowman Cake Chocolate 1x 60,000 60,000
Strawberry Log Cake 2x 105,000 210,000
Sub Total 385,000
GRAND TOTAL 385,000
VISA MASTER 385,000
8213
CHANGE 0
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"385,000"` | 385000 | |
| total | `"385,000"` | 385000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Chocolate Log Cake"` | `"115,000"` | `"115,000"` | Chocolate Log Cake | 115000 | 115000 | 1.0 | |
| 2 | `"Snowman Cake Chocolate"` | `"60,000"` | `"60,000"` | Snowman Cake Chocolate | 60000 | 60000 | 1.0 | |
| 3 | `"Strawberry Log Cake"` | `"105,000"` | `"210,000"` | Strawberry Log Cake | 105000 | 210000 | 2.0 | |

![test-082](audit/test-082.png)

---

## test-086

### Page text, as the model saw it

```
1 Cheezemania 9,500
1 Mamamia 12,500
SUBTOTAL 22,000
DUE 22,000
CASH 52,000
CHANGE 30,000
TOTAL QTY 2 ITEM 2 PCS
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"22,000"` | 22000 | |
| total | `"22,000"` | 22000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"Cheezemania"` | `null` | `"9,500"` | Cheezemania | None | 9500 | 1.0 | |
| 2 | `"Mamamia"` | `null` | `"12,500"` | Mamamia | None | 12500 | 1.0 | |

![test-086](audit/test-086.png)

---

## test-088

### Page text, as the model saw it

```
STIX ECLAIRS
1 x 19,000 19,000
ALMOND CREAM CHEESE
1 x 28,000 28,000
SUB TOTAL 47,000
GRAND TOTAL 47,000
VISA 8945 47,000
CHANGE DUE 0
```

### Scalars

| field | CORD raw | parsed | matches the page? |
|---|---|---|---|
| subtotal | `"47,000"` | 47000 | |
| total | `"47,000"` | 47000 | |

### Line items

| # | CORD nm | CORD unitprice | CORD price | parsed name | unit_price | price | qty | matches the page? |
|---|---|---|---|---|---|---|---|---|
| 1 | `"STIX ECLAIRS"` | `"19,000"` | `"19,000"` | STIX ECLAIRS | 19000 | 19000 | 1.0 | |
| 2 | `"ALMOND CREAM CHEESE"` | `"28,000"` | `"28,000"` | ALMOND CREAM CHEESE | 28000 | 28000 | 1.0 | |

![test-088](audit/test-088.png)

---
