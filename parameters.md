# Parameter table: what my simulator assumes vs what sources say

As of 2026-10-28 (Day 2). Educational project, not a medical device.

**How to read the Status column**

| Status | Meaning |
|---|---|
| Confirmed | A source I opened supports the value. |
| Partly | A source supports part of it, or only a range. |
| Derived | My own calculation from published data. Not a measurement. |
| Not sourced | I could not find or read a source. Still an assumption. |
| Contradicted | A source disagrees with what my simulator does. Needs fixing. |

"Opened" means I read the page itself. "Excerpt" means I only saw a search excerpt and still need to open it.

## Parameters

| # | Parameter | Day 1 value | What the sources say | Status | Action for the simulator |
|---|---|---|---|---|---|
| 1 | 31G needle outer / inner diameter | OD about 0.26 mm, ID 0.133 mm | Nominal 31G regular wall: OD 0.261 mm, ID 0.133 mm [1]. Thin-wall needles have the same OD but a larger ID [1]. | Confirmed (regular wall) | Pen needles are often thin-wall, so my bore is probably too small. Add a wall-type setting and find thin-wall IDs (ISO 9626 [1b]). |
| 2 | Needle length | 6 mm | The standard pen needle is 4 mm, used at 90 degrees. 5 mm and 6 mm are alternatives with a skin lift or an angle [4]. A common 32G pen needle is 0.23 mm x 4 mm [12]. The force studies used 5 mm (31G) and 6 mm (32G) needles [2][3]. | Contradicted (as a default) | Default to 4 mm. Keep 5 and 6 mm as options. |
| 3 | Insulin viscosity | 1.1 mPa.s ("about water") | Measured for commercial insulins at 20 C in a PLoS ONE paper [7], but the values are in a supplementary table I could not open. Concentrated proteins can be far more viscous and shear-thinning [8]. | Not sourced | Read Table S1 in [7] by hand. Add temperature dependence later (cold insulin). |
| 4 | Plunger (cartridge bore) diameter | 9.4 mm | A 3 mL cartridge is 11.6 mm outer diameter and 64.1 mm long [5]. The inner diameter is not stated. | Partly | My 9.4 mm is plausible but unconfirmed. Find the ISO 11608-3 drawing or a manufacturer drawing. |
| 5 | Stopper friction | 3 N (SD 0.35) | Cartridge supplier test limits: break-loose at most 15 N, glide at most 10 N [5b]. These are limits, not typical values. Extrapolating published force-vs-speed lines to zero speed gives 0.6 to 4.8 N depending on pen and needle (my fit, see below). | Derived | Use a wider prior, about 0.5 to 5 N. Treat the intercept as "zero-speed force", not pure friction. |
| 6 | Force vs push speed | Linear: F = friction + c.v | Measured force rises linearly with push speed for six pen and needle combinations (R squared 0.997 to 1.000). At 20 U and 3.3 to 8.3 mm/s, forces are 5.7 to 24.5 N [2]. | Confirmed (shape only) | Keep the linear model. Do not claim absolute force accuracy: those speeds are push-button speeds, and I do not yet know the pen's button-to-plunger ratio. |
| 7 | Injection speed ("normal" vs "fast") | Normal 2.4 to 7.6 U/s, fast 6.2 to 20.8 U/s (my conversion) | One pen study tested at 6 U/s [6]. That sits inside both of my ranges. | Contradicted | Redefine "fast" in U/s against a sourced reference. The lower end of my "fast" class is a normal test speed. |
| 8 | Hold time after the dose | 0.5 to 2.5 s | Manufacturer instructions say count 10 s before removing the needle [9][12]. A guideline summary says wait about 10 s [10]. A secondary memo about the 2025 FITTER update says at least 3 s, ideally 10 s [11]. | Contradicted | Model normal hold as 3 to 10 s and add a "hold too short" fault. |
| 9 | Dose and units | 20 U = 0.2 mL | U-100 means 100 units per mL (definition). | Confirmed | None. |
| 10 | Skin thickness | Illustrative layers | Mean skin thickness is about 2.0 to 2.5 mm (95% CI 1.3 to 3.3 mm) and similar across sites and groups. Subcutaneous fat varies widely with BMI and site [4]. | Confirmed | The 3D cross-section exaggerates layer thicknesses. Say so on screen. |

Notes on sources: [4] is a review by two employees of BD, a needle manufacturer. [2] compares Novo Nordisk's FlexPen with two competitors, so it is likely manufacturer-sponsored; I read only its abstract. [9] is a manufacturer leaflet.

## What published data says about my physics

The linear shape holds. All six published series are straight lines in push speed. This supports the form of the Day 1 model.

Several of my numbers need fixing:

1. **Gauge number is not bore.** For 20 U with a 31G thin-wall needle, SoloStar needed more force than with a 32G extra-thin-wall needle at every speed [2]. A thinner gauge needed less force. The abstract does not say why. My best guess is that the extra-thin wall leaves a larger bore, but the two needles also differ in length (5 mm vs 6 mm), so I have not shown it. Either way, my model must use the inner diameter and length, not the gauge number.
2. **Bore effect is large.** Flow resistance scales as 1/r^4. Using nominal regular-wall bores [1], a 32G needle has 2.3 times the resistance of a 31G, and a 30G has about half. See `figures/needle_resistance_vs_gauge.png`.
3. **Hold time and speed definitions need to follow sources.** See rows 7 and 8.

## Fits of the published force data (my calculation)

20 U, push speeds 3.3, 5.0 and 8.3 mm/s, data from [2]. Intercepts are extrapolated outside the measured range from three points, so they are rough.

| Pen + needle | Slope (N per mm/s) | Intercept (N) | R squared |
|---|---|---|---|
| FlexPen (NG) + 31G thin-wall | 1.50 | 3.18 | 1.000 |
| SoloStar + 31G thin-wall | 2.29 | 1.72 | 1.000 |
| KwikPen + 31G thin-wall | 2.39 | 4.76 | 0.999 |
| FlexPen (NG) + 32G extra-thin-wall | 1.40 | 1.15 | 1.000 |
| SoloStar + 32G extra-thin-wall | 1.90 | 0.61 | 0.997 |
| KwikPen + 32G extra-thin-wall | 2.51 | 0.71 | 1.000 |

Figure: `figures/published_force_vs_speed.png`.

## Still to find

- Thin-wall and extra-thin-wall inner diameters for 31G and 32G pen needles (ISO 9626 or manufacturer data).
- Viscosity values from Table S1 of [7].
- Cartridge inner diameter (ISO 11608-3 or a manufacturer drawing).
- Button-to-plunger travel ratio for at least one pen, so push-button speed can be converted to plunger speed.
- Open the full text of [2] and [3], and check their disclosures.

## Sources

1. Hamilton Company, "Needle Gauge Chart" (nominal OD, ID and wall thickness). Opened. https://www.hamiltoncompany.com/knowledge-base/article/needle-gauge-chart
   1b. ISO 9626:2016, stainless steel needle tubing (defines regular, thin, extra-thin and ultra-thin wall classes). Excerpt only. https://standards.iteh.ai/catalog/standards/sist/5917f266-c45c-43b2-8027-230958bfbbd9/sist-en-iso-9626-2016
2. Comparison of injection force of Next Generation FlexPen, SoloStar and KwikPen, Expert Opinion on Pharmacotherapy, 2009 (abstract). Opened. https://informahealthcare.com/doi/abs/10.1517/14656560903018929
3. Rissler et al., "Evaluation of the injection force dynamics of a modified prefilled insulin pen", Expert Opinion on Pharmacotherapy 2008;9(13):2217. Excerpt only. https://www.lunduniversity.lu.se/lup/publication/2cd16c3e-b025-44b2-974d-4938043fb841
4. Hirsch and Strauss, "The Injection Technique Factor", Clinical Diabetes 2019;37(3):227. Opened. Authors are BD employees. https://pmc.ncbi.nlm.nih.gov/articles/PMC6640874/
5. Nest Scientific, 3.0 mL cartridge (OD 11.6 mm, height 64.1 mm). Opened. https://www.nestscientificusa.com/medical-products/3-0ml-ready-to-use-rtu-cartridge-assembly-with-short-stopper-1-tube-100-cartridges.html
   5b. Nest Scientific, 3 mL cartridge (break-loose and glide force limits). Excerpt only. https://www.nestscientificusa.com/3-0-ml-ready-to-use-rtu-cartridge-assembly-with-shorts-stopper-100-cartridges-box-100-stoppers-bag-and-500-cartridges-500-stoppers-cs.html
6. J Diabetes Sci Technol, comparison of three disposable pens (injection speed 6 U/s). Excerpt only. https://journals.sagepub.com/doi/xml/10.1177/1932296815601441
7. Adams et al., "Characterisation of insulin analogues therapeutically available to patients", PLoS ONE 2018. Opened; viscosity values are in supplementary Table S1, not read. https://pmc.ncbi.nlm.nih.gov/articles/PMC5875863/
8. Rheosense, injectability application note. Excerpt only. https://www.rheosense.com/applications/viscosity/drug-injectability
9. BD, "Injection technique for different needle lengths" (manufacturer leaflet). Excerpt only. https://static.bd.com/assets/product/Documents/Diabetes%20Care%20(DC)/DC_Injection-technique-for-different-needle-lengths_BR_EN.pdf
10. Guideline Central, summary of the FITTER Forward injection-technique recommendations. Excerpt only. https://www.guidelinecentral.com/insights/advance-insulin-injection-technique-guidelines-spotlight/
11. Close Concerns memo on the 2025 FITTER Forward recommendations (secondary source). Excerpt only. https://cckb.closeconcerns.com/r/290770ef/pdf
12. BD, 4 mm pen needle worksheet (0.23 mm x 4 mm, 32G). Excerpt only. https://go.bd.com/rs/565-YXD-236/images/BD%20Pen%20Needle%20IT%20Worksheet%20TearPad_19-014_HI.pdf
