# Footage credits

SceneGap Edge was evaluated on 44 openly licensed video clips from [Wikimedia Commons](https://commons.wikimedia.org/).
The clips themselves are not in this repository. `datasets/manifests/commons_manifest.json` lists each one with its
Commons page, download URL, licence, author and the SHA-256 of the original and of the H.264 transcode, so the same
set can be rebuilt with `scripts/fetch_commons.py` (see the README).

The screenshots in `docs/screenshots/`, the GIFs in `docs/media/`, the proposal deck and the demo video show frames
from these clips. Those frames stay under the licence of the clip they come from, with the attribution below; an
image that contains frames from a CC BY-SA clip is shared under the same CC BY-SA licence. The clips used in the
live demo are marked in the **Demo** column.

Author names are the `attribution` field of the manifest, taken from each Commons file page. Split is the
evaluation side (`eval/split.py`): dev clips set the threshold, test clips were scored once.

| # | Title on Commons | Author | Licence | Split | Demo | Commons page |
|---|---|---|---|---|---|---|
| 000 | Cadaques cafe de la habana 2008 august converted YAN3.ogv | Cliché Online (Yan.) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Cadaques_cafe_de_la_habana_2008_august_converted_YAN3.ogv) |
| 001 | Vichy - Grand Café, terrasse sous la grêle.ogv | Romainbehar | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Vichy_-_Grand_Caf%C3%A9,_terrasse_sous_la_gr%C3%AAle.ogv) |
| 002 | Merry X-mas at Kranzler.webm | C.Suthorn | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Merry_X-mas_at_Kranzler.webm) |
| 003 | Times Cafe inflatable waving character.webm | Andy Li | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Times_Cafe_inflatable_waving_character.webm) |
| 004 | Rateel cafe music2.webm | Iainsimpsonstewart | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | test |  | [link](https://commons.wikimedia.org/wiki/File:Rateel_cafe_music2.webm) |
| 005 | Starbucks en la aĉetcentro Kristall (Tjumeno).webm | RG72 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Starbucks_en_la_a%C4%89etcentro_Kristall_(Tjumeno).webm) |
| 006 | Interior Paragon Café Katoomba.ogv | Bluedawe | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Interior_Paragon_Caf%C3%A9_Katoomba.ogv) |
| 007 | Café Lomi, Paris - Vimeo.webm | ideafarm films | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Caf%C3%A9_Lomi,_Paris_-_Vimeo.webm) |
| 008 | Operation Ghost Stories - Video 01.webm | FBI – Federal Bureau of Investigation | Public domain | dev |  | [link](https://commons.wikimedia.org/wiki/File:Operation_Ghost_Stories_-_Video_01.webm) |
| 009 | Coffee Bean & Tea Leaf Process.webm | Kelliks | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Coffee_Bean_%26_Tea_Leaf_Process.webm) |
| 010 | “走线客”过境墨西哥 不忘来杯星巴克.webm | 美国之音中文网 | Public domain | dev |  | [link](https://commons.wikimedia.org/wiki/File:%E2%80%9C%E8%B5%B0%E7%BA%BF%E5%AE%A2%E2%80%9D%E8%BF%87%E5%A2%83%E5%A2%A8%E8%A5%BF%E5%93%A5_%E4%B8%8D%E5%BF%98%E6%9D%A5%E6%9D%AF%E6%98%9F%E5%B7%B4%E5%85%8B.webm) |
| 011 | Color sorter coffeebeans.webm | AlexanderKlink | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | test |  | [link](https://commons.wikimedia.org/wiki/File:Color_sorter_coffeebeans.webm) |
| 012 | Kaffe - Ystad-2024.ogg | Jonn Leffmann | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | dev | yes | [link](https://commons.wikimedia.org/wiki/File:Kaffe_-_Ystad-2024.ogg) |
| 013 | Coffee from dan 2.webm | Denis kasozi | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Coffee_from_dan_2.webm) |
| 014 | Traditional Ethiopian Coffee Roasting Ceremony.webm | Keria T | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Traditional_Ethiopian_Coffee_Roasting_Ceremony.webm) |
| 015 | Despulpadora.ogg | Jhonespe150102 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Despulpadora.ogg) |
| 016 | Lions Almelo zamelt koffie in voor Voedselbank.webm | AAVISIE | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | dev | yes | [link](https://commons.wikimedia.org/wiki/File:Lions_Almelo_zamelt_koffie_in_voor_Voedselbank.webm) |
| 017 | Sunday Morning Espresso Routine - Grind + distribute + tamp + extraction (15-Second Abridged Version).webm | Scott Schiller from San Francisco, CA, USA | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Sunday_Morning_Espresso_Routine_-_Grind_%2B_distribute_%2B_tamp_%2B_extraction_(15-Second_Abridged_Version).webm) |
| 018 | Кофемельница JURA 43.webm | Gontcharik.petr | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:%D0%9A%D0%BE%D1%84%D0%B5%D0%BC%D0%B5%D0%BB%D1%8C%D0%BD%D0%B8%D1%86%D0%B0_JURA_43.webm) |
| 019 | MoliendoCafeEnLicuadora ohs02.webm | PetrohsW | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:MoliendoCafeEnLicuadora_ohs02.webm) |
| 020 | Espresso video.ogv | Rosatrieu | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Espresso_video.ogv) |
| 021 | Macro Espresso Process.webm | Scott Schiller from San Francisco, CA, USA | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Macro_Espresso_Process.webm) |
| 022 | Der perfekte Espresso aus dem Siebträger.ogv | Max Duchardt, Katrin Engel | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | dev | yes | [link](https://commons.wikimedia.org/wiki/File:Der_perfekte_Espresso_aus_dem_Siebtr%C3%A4ger.ogv) |
| 023 | Pour Over.ogv | Lev Lazinskiy | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Pour_Over.ogv) |
| 024 | Use of a coffee press.ogv | Daniel Case | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Use_of_a_coffee_press.ogv) |
| 025 | Schritt für Schritt - Kaffeezubereitung mit der Chemex.ogv | Max Duchardt, Katrin Engel | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Schritt_f%C3%BCr_Schritt_-_Kaffeezubereitung_mit_der_Chemex.ogv) |
| 026 | Latte art flower - 01.ogv | Anna Frodesiak | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Latte_art_flower_-_01.ogv) |
| 027 | Latte art leaf - 01.ogv | Anna Frodesiak | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | test |  | [link](https://commons.wikimedia.org/wiki/File:Latte_art_leaf_-_01.ogv) |
| 028 | Nespresso machine.ogv | Kjetil Ree | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Nespresso_machine.ogv) |
| 029 | A man pours Arabic coffee.ogv | Sarah Canbel | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:A_man_pours_Arabic_coffee.ogv) |
| 030 | Servido tradicional de café etíope.webm | ProtoplasmaKid | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Servido_tradicional_de_caf%C3%A9_et%C3%ADope.webm) |
| 031 | How to brew Coffee using the laws of physics - with the Hario Syphon Technica.webm | Coffee Circle | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:How_to_brew_Coffee_using_the_laws_of_physics_-_with_the_Hario_Syphon_Technica.webm) |
| 032 | Sugar falling into coffee.webm | Anselm Schüler | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Sugar_falling_into_coffee.webm) |
| 033 | Bosnian coffee with rahat lokum, Kujundziluk and Old Bridge in Mostar - Bosnia and Herzegovina (2026)-bs.webm | Minja Klarić | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Bosnian_coffee_with_rahat_lokum,_Kujundziluk_and_Old_Bridge_in_Mostar_-_Bosnia_and_Herzegovina_(2026)-bs.webm) |
| 034 | A cup of Kenyan Coffee.webm | Queen Asali | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:A_cup_of_Kenyan_Coffee.webm) |
| 035 | Latte salute.webm | The White House | Public domain | dev |  | [link](https://commons.wikimedia.org/wiki/File:Latte_salute.webm) |
| 036 | Turkish tea 2015.webm | Klapi | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Turkish_tea_2015.webm) |
| 037 | Jane pouring beer fast.webm | Angulidayaaluta | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:Jane_pouring_beer_fast.webm) |
| 038 | Turkovich Family Wines - June 2019 - Stierch 03.ogv | Missvain | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Turkovich_Family_Wines_-_June_2019_-_Stierch_03.ogv) |
| 039 | Drinking glass symphony.ogv | IMG 4512 | [CC0](http://creativecommons.org/publicdomain/zero/1.0/deed.en) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Drinking_glass_symphony.ogv) |
| 040 | Thermochromic mug.webm | The wub | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Thermochromic_mug.webm) |
| 041 | Empty Streets of Paris COVID19.webm | CreatorsCloud | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | test | yes | [link](https://commons.wikimedia.org/wiki/File:Empty_Streets_of_Paris_COVID19.webm) |
| 042 | IrishTraditionalMusic-IrishPub-Tokyo-2016-2-24.webm | Nesnad | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | test |  | [link](https://commons.wikimedia.org/wiki/File:IrishTraditionalMusic-IrishPub-Tokyo-2016-2-24.webm) |
| 043 | Couple holding hands.webm | YouTube user “Editor” | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | dev |  | [link](https://commons.wikimedia.org/wiki/File:Couple_holding_hands.webm) |

Licence counts: CC BY-SA 4.0 (15), CC BY 3.0 (9), CC0 (8), CC BY-SA 3.0 (4), public domain (3), CC BY 4.0 (3),
CC BY 2.0 (2). Clips with NC (non-commercial) or ND (no derivatives) terms were excluded when the set was built.
