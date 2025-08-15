
import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta

# ---------------------- CONFIG ----------------------
st.set_page_config(
    page_title="Ma Boulangerie – Marges • Fournisseurs • Planning",
    page_icon="📊",
    layout="wide",
)

# ---------------------- DONNÉES RÉGLEMENTAIRES ----------------------
INCO_ALLERGENS = [
    "Gluten", "Crustacés", "Œufs", "Poissons", "Arachides", "Soja", "Lait",
    "Fruits à coque", "Céleri", "Moutarde", "Sésame", "Anhydride sulfureux et sulfites",
    "Lupin", "Mollusques",
]

# ---------------------- HELPERS ----------------------
def fmt_eur(x):
    try:
        return f"{x:,.2f} €".replace(",", " ").replace(".", ",")
    except Exception:
        return x

def hours_between(t1: time, t2: time) -> float:
    dt1 = datetime.combine(date.today(), t1)
    dt2 = datetime.combine(date.today(), t2)
    if dt2 < dt1:  # passes midnight
        dt2 += timedelta(days=1)
    return (dt2 - dt1).seconds / 3600

def labor_cost_per_unit(minutes_per_unit: float, hourly_rate: float, charges_pct: float, prime_h=0.0) -> float:
    hours = minutes_per_unit / 60.0
    return hours * (hourly_rate + prime_h) * (1 + charges_pct / 100)

def overhead_allocation_per_unit(monthly_overheads: float, monthly_volume_units: float) -> float:
    if monthly_volume_units <= 0:
        return 0.0
    return monthly_overheads / monthly_volume_units

def compute_margin(purchase_ht: float, labor_unit: float, overhead_unit: float, tva_pct: float, selling_ttc: float) -> dict:
    cost_ht = purchase_ht + labor_unit + overhead_unit
    tva_rate = tva_pct / 100
    selling_ht = selling_ttc / (1 + tva_rate) if (1 + tva_rate) else selling_ttc
    margin_ht = selling_ht - cost_ht
    margin_pct_on_sell = 0.0 if selling_ht == 0 else margin_ht / selling_ht * 100
    markup_pct_on_cost = 0.0 if cost_ht == 0 else margin_ht / cost_ht * 100
    return {
        "Coût d'achat HT": purchase_ht,
        "Coût MO / unité": labor_unit,
        "Frais fixes / unité": overhead_unit,
        "Coût de revient HT": cost_ht,
        "Prix de vente HT": selling_ht,
        "Prix de vente TTC": selling_ttc,
        "Marge HT": margin_ht,
        "% marge sur PV HT": margin_pct_on_sell,
        "% coeff sur coût": markup_pct_on_cost,
    }

# ---------------------- INIT (charge depuis CSV si présents) ----------------------
def load_csv_or_default(name, default_df):
    try:
        return pd.read_csv(name)
    except Exception:
        return default_df.copy()

products = load_csv_or_default("products.csv", pd.DataFrame([
    {"SKU": "BAG-TRAD", "Produit": "Baguette traditionnelle", "Catégorie": "Boulangerie", "Prix vente TTC": 1.20, "TVA %": 5.5, "Allergènes": "Gluten", "Stock": 120, "Seuil alerte": 30},
    {"SKU": "CRO-BA", "Produit": "Croissant beurre", "Catégorie": "Viennoiserie", "Prix vente TTC": 1.10, "TVA %": 5.5, "Allergènes": "Gluten;Lait;Œufs", "Stock": 80, "Seuil alerte": 20},
]))
suppliers = load_csv_or_default("suppliers.csv", pd.DataFrame([
    {"Fournisseur": "Moulins Dupont", "Contact": "dupont@moulins.fr", "Téléphone": "+33 1 23 45 67 89", "Délai (j)": 2},
    {"Fournisseur": "Beurres de Normandie", "Contact": "ventes@beurres.fr", "Téléphone": "+33 2 12 34 56 78", "Délai (j)": 3},
    {"Fournisseur": "Grossiste Paris", "Contact": "contact@grossiste.paris", "Téléphone": "+33 1 98 76 54 32", "Délai (j)": 1},
]))
supplier_prices = load_csv_or_default("supplier_prices.csv", pd.DataFrame([
    {"SKU": "BAG-TRAD", "Fournisseur": "Moulins Dupont", "Unité": "pièce", "Prix HT": 0.35, "Qté / unité": 1.0, "MOQ": 50},
    {"SKU": "BAG-TRAD", "Fournisseur": "Grossiste Paris", "Unité": "pièce", "Prix HT": 0.33, "Qté / unité": 1.0, "MOQ": 80},
    {"SKU": "CRO-BA", "Fournisseur": "Beurres de Normandie", "Unité": "pièce", "Prix HT": 0.42, "Qté / unité": 1.0, "MOQ": 40},
    {"SKU": "CRO-BA", "Fournisseur": "Grossiste Paris", "Unité": "pièce", "Prix HT": 0.45, "Qté / unité": 1.0, "MOQ": 60},
]))
ingredients = load_csv_or_default("ingredients.csv", pd.DataFrame([
    {"Code ingrédient": "FARINE-T45", "Nom": "Farine T45", "Unité achat": "kg"},
    {"Code ingrédient": "BEURRE-AOC", "Nom": "Beurre AOP", "Unité achat": "kg"},
    {"Code ingrédient": "LEVURE-B", "Nom": "Levure boulangère", "Unité achat": "kg"},
]))
ingredient_prices = load_csv_or_default("ingredient_prices.csv", pd.DataFrame([
    {"Code ingrédient": "FARINE-T45", "Fournisseur": "Moulins Dupont", "Prix HT / unité": 0.80, "Qté / unité": 1.0},
    {"Code ingrédient": "FARINE-T45", "Fournisseur": "Grossiste Paris", "Prix HT / unité": 0.78, "Qté / unité": 1.0},
    {"Code ingrédient": "BEURRE-AOC", "Fournisseur": "Beurres de Normandie", "Prix HT / unité": 7.20, "Qté / unité": 1.0},
    {"Code ingrédient": "LEVURE-B", "Fournisseur": "Grossiste Paris", "Prix HT / unité": 3.50, "Qté / unité": 1.0},
]))
recipes = load_csv_or_default("recipes.csv", pd.DataFrame([
    {"SKU": "BAG-TRAD", "Ingrédient": "FARINE-T45", "Qté par unité": 0.20, "Unité": "kg"},
    {"SKU": "BAG-TRAD", "Ingrédient": "LEVURE-B", "Qté par unité": 0.005, "Unité": "kg"},
    {"SKU": "CRO-BA", "Ingrédient": "FARINE-T45", "Qté par unité": 0.08, "Unité": "kg"},
    {"SKU": "CRO-BA", "Ingrédient": "BEURRE-AOC", "Qté par unité": 0.035, "Unité": "kg"},
]))
overheads = load_csv_or_default("overheads.csv", pd.DataFrame([
    {"Intitulé": "Loyer", "Montant mensuel €": 1500},
    {"Intitulé": "Énergie", "Montant mensuel €": 600},
    {"Intitulé": "Assurance", "Montant mensuel €": 120},
    {"Intitulé": "Divers", "Montant mensuel €": 180},
]))
employees = load_csv_or_default("employees.csv", pd.DataFrame([
    {"Employé": "Alice", "Rôle": "Boulangère", "Taux horaire €": 14.0, "Prime €/h": 0.0, "Charges %": 42.0},
    {"Employé": "Bruno", "Rôle": "Vente", "Taux horaire €": 12.0, "Prime €/h": 0.5, "Charges %": 38.0},
]))
shifts = load_csv_or_default("shifts.csv", pd.DataFrame([
    {"Date": (date.today()).isoformat(), "Employé": "Alice", "Rôle": "Boulangère", "Début": "05:00", "Fin": "13:00"},
    {"Date": (date.today() + timedelta(days=1)).isoformat(), "Employé": "Bruno", "Rôle": "Vente", "Début": "08:00", "Fin": "14:00"},
]))

# ---------------------- UI ----------------------
st.title("📊 Ma Boulangerie – Marges • Fournisseurs • Planning du personnel")
st.caption("Calculez vos marges, comparez les tarifs fournisseurs par produit, suivez les stocks & allergènes, et gérez le planning hebdomadaire du personnel.")

# KPI bar
colA, colB, colC = st.columns(3)
with colA:
    st.metric("Produits", len(products))
with colB:
    low_stock = int((products["Stock"] <= products["Seuil alerte"]).sum()) if {"Stock","Seuil alerte"}.issubset(products.columns) else 0
    st.metric("Ruptures potentielles", low_stock)
with colC:
    monthly_overheads_total = float(overheads["Montant mensuel €"].sum()) if len(overheads) else 0
    st.metric("Frais fixes mensuels", fmt_eur(monthly_overheads_total))

# Tabs
onglets = st.tabs([
    "📦 Catalogue & Fournisseurs",
    "🧾 Inventaire & Allergènes",
    "🥣 Ingrédients & Recettes",
    "💶 Prix & Marges",
    "🗓️ Planning du personnel",
    "⚙️ Paramètres • Import/Export",
])

# ---------------------- TAB 0: Catalogue & Suppliers ----------------------
with onglets[0]:
    st.subheader("Produits")
    st.markdown("Ajoutez vos produits, le prix de vente TTC, la TVA, les allergènes et les seuils de stock.")
    products = st.data_editor(products, num_rows="dynamic", use_container_width=True, key="products_editor")

    st.divider()
    cols = st.columns(2)
    with cols[0]:
        st.subheader("Fournisseurs")
        suppliers = st.data_editor(suppliers, num_rows="dynamic", use_container_width=True, key="suppliers_editor")
    with cols[1]:
        st.subheader("Tarifs par produit")
        st.caption("Saisissez un tarif HT par fournisseur et par SKU (même produit).")
        supplier_prices = st.data_editor(supplier_prices, num_rows="dynamic", use_container_width=True, key="supplier_prices_editor")

    st.divider()
    st.subheader("Comparer les fournisseurs pour un produit")
    if len(products) > 0:
        sku = st.selectbox("Sélectionnez un produit (SKU)", products["SKU"].unique())
        dfp = supplier_prices.query("SKU == @sku").copy()
        if dfp.empty:
            st.info("Aucun tarif fournisseur renseigné pour ce SKU.")
        else:
            best_idx = dfp["Prix HT"].astype(float).idxmin()
            dfp.loc[best_idx, "Meilleur"] = "✅"
            dfp_sorted = dfp.sort_values("Prix HT")
            st.dataframe(dfp_sorted.style.format({"Prix HT": fmt_eur}).highlight_min(subset=["Prix HT"], color="#d1ffd6"), use_container_width=True)
    else:
        st.info("Ajoutez d'abord des produits.")

# ---------------------- TAB 1: Inventory & Allergens ----------------------
with onglets[1]:
    st.subheader("Inventaire & Allergènes (INCO)")
    st.markdown("Mettez à jour les stocks et gérez les **14 allergènes réglementaires INCO**.")
    df = products.copy()

    # Allergènes : multipick avec INCO, serialisé en texte "a;b;c"
    if "Allergènes" in df.columns:
        for i, row in df.iterrows():
            current = row.get("Allergènes", "")
            if isinstance(current, str):
                current_list = [x.strip() for x in current.split(";") if x.strip()]
            elif isinstance(current, list):
                current_list = current
            else:
                current_list = []
            sel = st.multiselect(f"Allergènes – {row['Produit']} ({row['SKU']})", INCO_ALLERGENS, default=current_list, key=f"alg_{row['SKU']}")
            df.at[i, "Allergènes"] = ";".join(sel)
        products = df

    # Low stock
    if not {"Stock", "Seuil alerte"}.issubset(products.columns):
        st.warning("Ajoutez les colonnes 'Stock' et 'Seuil alerte' dans Produits.")
    else:
        low = products[products["Stock"] <= products["Seuil alerte"]]
        if low.empty:
            st.success("Aucun produit sous le seuil d'alerte ✅")
        else:
            st.error("Produits sous seuil d'alerte :")
            st.dataframe(low[["SKU","Produit","Stock","Seuil alerte"]], use_container_width=True)

    st.markdown("### Export étiquette INCO")
    incotbl = products[["SKU","Produit","Allergènes"]].copy()
    st.dataframe(incotbl, use_container_width=True)

# ---------------------- TAB 2: Ingredients & Recipes ----------------------
with onglets[2]:
    st.subheader("Ingrédients & Recettes (BOM)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Catalogue ingrédients**")
        ingredients = st.data_editor(ingredients, num_rows="dynamic", use_container_width=True, key="ingredients_editor")
        st.markdown("**Tarifs ingrédients (HT)** — le calcul de recette prendra le **meilleur prix**.")
        ingredient_prices = st.data_editor(ingredient_prices, num_rows="dynamic", use_container_width=True, key="ingredient_prices_editor")
    with c2:
        st.markdown("**Recettes par produit (quantité d'ingrédient par unité produite)**")
        recipes = st.data_editor(recipes, num_rows="dynamic", use_container_width=True, key="recipes_editor")

    st.divider()
    st.markdown("### Calcul du **coût matières HT** par produit")

    best_price = (ingredient_prices
                  .sort_values(["Code ingrédient","Prix HT / unité"])
                  .groupby("Code ingrédient").first()["Prix HT / unité"].to_dict())

    def cost_from_recipe(sku: str) -> float:
        sub = recipes.query("SKU == @sku")
        total = 0.0
        for _, r in sub.iterrows():
            p = best_price.get(r["Ingrédient"], 0.0)
            q = float(r["Qté par unité"])
            total += p * q
        return total

    if len(products):
        sku_sel = st.selectbox("Produit (SKU)", products["SKU"].tolist(), key="sku_recipe_calc")
        cm = cost_from_recipe(sku_sel)
        st.metric("Coût matières d'une unité (HT)", fmt_eur(cm))
        if st.button("➡️ Enregistrer ce coût comme 'Recette calculée'"):
            new_row = {"SKU": sku_sel, "Fournisseur": "Recette calculée", "Unité": "unité", "Prix HT": round(cm, 4), "Qté / unité": 1.0, "MOQ": 0}
            sp = supplier_prices.copy()
            sp = sp[~((sp["SKU"] == sku_sel) & (sp["Fournisseur"] == "Recette calculée"))]
            supplier_prices = pd.concat([sp, pd.DataFrame([new_row])], ignore_index=True)
            st.success("Coût matières appliqué ✔️ — sélectionnez 'Recette calculée' comme fournisseur dans l'onglet Marges.")

# ---------------------- TAB 3: Pricing & Margins ----------------------
with onglets[3]:
    st.subheader("Calculateur de marge par produit")
    if len(products) == 0:
        st.warning("Ajoutez au moins un produit dans l'onglet Catalogue.")
    else:
        left, right = st.columns([2, 1])
        with left:
            sku = st.selectbox("Produit (SKU)", products["SKU"])  # select by SKU
            product_row = products.set_index("SKU").loc[sku]
            prod_name = product_row["Produit"]
            tva_pct_default = float(product_row.get("TVA %", 0))
            selling_ttc_default = float(product_row.get("Prix vente TTC", 0))

            st.markdown(f"**Produit :** {prod_name}")
            suppliers_sku = supplier_prices.query("SKU == @sku")
            if suppliers_sku.empty:
                st.info("Renseignez un tarif fournisseur ou utilisez l'onglet Recettes pour calculer le coût matières.")
            else:
                sup_choice = st.selectbox("Source du coût d'achat", suppliers_sku["Fournisseur"].unique(), key="sup_for_margin")
                purchase_ht = float(suppliers_sku.set_index("Fournisseur").loc[sup_choice, "Prix HT"])  # HT par unité

                st.markdown("**Paramètres de production**")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    minutes_per_unit = st.number_input("Minutes de MO / unité", min_value=0.0, step=1.0, value=3.0)
                with c2:
                    hourly_rate = st.number_input("Taux horaire (€)", min_value=0.0, step=0.5, value=14.0)
                with c3:
                    charges_pct = st.number_input("Charges employeur (%)", min_value=0.0, step=1.0, value=42.0)
                with c4:
                    prime_h = st.number_input("Prime €/h", min_value=0.0, step=0.1, value=0.0)

                st.markdown("**Frais fixes**")
                monthly_overheads_total = float(overheads["Montant mensuel €"].sum())
                c4, c5 = st.columns(2)
                with c4:
                    monthly_volume = st.number_input("Volume mensuel prévu (unités)", min_value=1, step=50, value=5000)
                with c5:
                    tva_pct = st.number_input("TVA (%)", min_value=0.0, step=0.5, value=float(tva_pct_default))

                overhead_unit = overhead_allocation_per_unit(monthly_overheads_total, monthly_volume)
                labor_unit = labor_cost_per_unit(minutes_per_unit, hourly_rate, charges_pct, prime_h)

                st.markdown("**Prix de vente**")
                selling_ttc = st.number_input("Prix de vente TTC (€)", min_value=0.0, step=0.05, value=float(selling_ttc_default))

                results = compute_margin(purchase_ht, labor_unit, overhead_unit, tva_pct, selling_ttc)

                st.divider()
                st.markdown("### Résultats")
                met_cols = st.columns(3)
                met_cols[0].metric("Coût de revient HT", fmt_eur(results["Coût de revient HT"]))
                met_cols[1].metric("Marge HT / unité", fmt_eur(results["Marge HT"]))
                met_cols[2].metric("% marge sur PV HT", f"{results['% marge sur PV HT']:.1f} %")

                st.markdown("#### Détail")
                detail = pd.DataFrame([
                    {"Poste": "Achat (matières / unité)", "Montant": results["Coût d'achat HT"]},
                    {"Poste": "Main d'œuvre / unité", "Montant": results["Coût MO / unité"]},
                    {"Poste": "Frais fixes / unité", "Montant": results["Frais fixes / unité"]},
                    {"Poste": "Coût de revient HT", "Montant": results["Coût de revient HT"]},
                    {"Poste": "Prix de vente HT", "Montant": results["Prix de vente HT"]},
                ])
                st.dataframe(detail.style.format({"Montant": fmt_eur}), use_container_width=True)

        with right:
            st.markdown("### Raccourcis")
            st.info(
                """
                - **Coût d'achat** : choisissez un fournisseur ou la ligne spéciale **Recette calculée**.
                - **Charges %** : charges patronales estimées.
                - **Prime €/h** : primes fixes à l'heure (ex: nuit, froid, ancienneté).
                - **Frais fixes** ventilés par unité via le volume mensuel.
                """
            )

# ---------------------- TAB 4: Staff Scheduling ----------------------
with onglets[4]:
    st.subheader("Planning hebdomadaire")
    # Ajout rapide
    cols = st.columns(5)
    with cols[0]:
        week_monday = st.date_input("Semaine - lundi", date.today() - timedelta(days=date.today().weekday()))
    with cols[1]:
        emp_names = employees["Employé"].tolist()
        emp_sel = st.selectbox("Employé", emp_names)
    with cols[2]:
        role = st.text_input("Rôle", value=employees.set_index("Employé").get("Rôle", pd.Series()).get(emp_sel, "Vente"))
    with cols[3]:
        start_str = st.text_input("Début (HH:MM)", value="08:00")
    with cols[4]:
        end_str = st.text_input("Fin (HH:MM)", value="12:00")

    if st.button("➕ Ajouter shift (lundi)"):
        new_row = {"Date": week_monday.isoformat(), "Employé": emp_sel, "Rôle": role, "Début": start_str, "Fin": end_str}
        shifts = pd.concat([shifts, pd.DataFrame([new_row])], ignore_index=True)
        st.success("Shift ajouté ✔️")

    # Filtre semaine
    week_end = week_monday + timedelta(days=6)
    df_shifts = shifts.copy()
    try:
        df_shifts["Date_dt"] = pd.to_datetime(df_shifts["Date"]).dt.date
    except Exception:
        df_shifts["Date_dt"] = week_monday  # fallback
    mask = (df_shifts["Date_dt"] >= week_monday) & (df_shifts["Date_dt"] <= week_end)
    df_shifts = df_shifts[mask].copy()

    # Calcul heures & coûts (simple: taux horaire + prime/h, charges %)
    emp_map = employees.set_index("Employé").to_dict(orient="index")
    def calc_hours_and_cost(row):
        try:
            h1 = datetime.strptime(str(row["Début"]), "%H:%M").time()
            h2 = datetime.strptime(str(row["Fin"]), "%H:%M").time()
            hrs = hours_between(h1, h2)
        except Exception:
            hrs = 0.0
        emp = row.get("Employé")
        taux = float(emp_map.get(emp, {}).get("Taux horaire €", 0.0))
        prime = float(emp_map.get(emp, {}).get("Prime €/h", 0.0))
        charges = float(emp_map.get(emp, {}).get("Charges %", 0.0))
        cost = hrs * (taux + prime) * (1 + charges/100.0)
        return pd.Series({"Heures": round(hrs,2), "Coût chargé €": round(cost,2)})

    if not df_shifts.empty:
        extras = df_shifts.apply(calc_hours_and_cost, axis=1)
        df_display = pd.concat([df_shifts.reset_index(drop=True), extras], axis=1)
        st.data_editor(df_display.drop(columns=["Date_dt"]), num_rows="dynamic", use_container_width=True, key="shifts_editor")
        st.metric("Heures totales (semaine)", f"{df_display['Heures'].sum():.2f} h")
        st.metric("Coût salarial chargé (semaine)", fmt_eur(df_display["Coût chargé €"].sum()))
        st.download_button("📥 Exporter la semaine (CSV)", df_display.drop(columns=["Date_dt"]).to_csv(index=False).encode("utf-8"),
                           file_name=f"planning_{week_monday.isoformat()}.csv", mime="text/csv")
    else:
        st.info("Aucun shift cette semaine.")

# ---------------------- TAB 5: Settings / Import Export ----------------------
with onglets[5]:
    st.subheader("Frais fixes (mensuels)")
    overheads = st.data_editor(overheads, num_rows="dynamic", use_container_width=True, key="overheads_editor")

    st.subheader("Employés")
    employees = st.data_editor(employees, num_rows="dynamic", use_container_width=True, key="employees_editor")

    st.divider()
    st.markdown("### Exporter les données (CSV)")
    for label, df, fname in [
        ("Produits", products, "products.csv"),
        ("Fournisseurs", suppliers, "suppliers.csv"),
        ("Tarifs produits", supplier_prices, "supplier_prices.csv"),
        ("Ingrédients", ingredients, "ingredients.csv"),
        ("Tarifs ingrédients", ingredient_prices, "ingredient_prices.csv"),
        ("Recettes", recipes, "recipes.csv"),
        ("Employés", employees, "employees.csv"),
        ("Frais fixes", overheads, "overheads.csv"),
        ("Shifts", shifts, "shifts.csv"),
    ]:
        st.download_button(f"📥 Exporter {label}", df.to_csv(index=False).encode("utf-8"), file_name=fname, mime="text/csv")

st.caption("Conseil : utilisez l'onglet **Recettes** pour générer automatiquement le coût matières, puis sélectionnez **Recette calculée** dans l'onglet **Marges**.")
