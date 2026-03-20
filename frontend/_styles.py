"""CSS global — thème sombre DS_COVID."""

DARK_THEME_CSS = """
<style>
html, body, [class*="css"] {
    font-family: "Roboto", "Montserrat", sans-serif;
    background-color: #071022 !important;
    color: #e6eef6 !important;
}

.hero-header {
    padding: 20px;
    margin-bottom: 18px;
    border-radius: 12px;
    font-size: 26px;
    font-weight: 600;
    text-align: center;
    background-size: 200% 200%;
    color: #fff;
    animation: gradientShift 6s ease infinite, pulse 2s infinite;
}

@keyframes gradientShift {
    0%{background-position:0% 50%;}
    50%{background-position:100% 50%;}
    100%{background-position:0% 50%;}
}
@keyframes pulse {
    0%{transform:scale(1);}
    50%{transform:scale(1.02);}
    100%{transform:scale(1);}
}

.stTabs [role="tablist"] button {
    padding: 8px 14px;
    border-radius: 6px 6px 0 0;
    margin-right: 3px;
    font-weight:600;
    transition: all 0.3s ease;
}
.stTabs [role="tablist"] button[aria-selected="true"] {
    background: linear-gradient(90deg, #0f204f, #1a296b);
    color:#fff !important;
    box-shadow: 0 3px 8px #00000080;
}
.stTabs [role="tablist"] button:hover {
    transform: scale(1.03);
}

.card {
    background-color: #131a2b;
    padding: 14px;
    margin: 10px 0;
    border-radius: 10px;
    box-shadow: 1px 1px 8px #00000080;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.card:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 2px 4px 12px #000000a0;
}

.badge {
    display:inline-block;
    background:#0f204f;
    color:#fff;
    padding: 2px 6px;
    border-radius:8px;
    margin-left:6px;
    font-size:11px;
    animation: pulseBadge 1.5s infinite alternate;
}
@keyframes pulseBadge {
    0%{transform: scale(1);}
    100%{transform: scale(1.2);}
}
</style>
"""
