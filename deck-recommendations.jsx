import { useState } from "react";

const DECKS = {
  buildable: [
    {
      id: "charizard",
      name: "Mega Charizard Y ex",
      tier: "S",
      type: "Fire",
      typeColor: "#ef4444",
      typeBg: "#450a0a",
      emoji: "🔥",
      rating: 5,
      strategy: "Charmeleon's Ignition gives a free Fire energy on evolve. Moltres ex loads the bench. Serena guarantees you find the Mega ex. Rare Candy skips to Mega Charizard turn 2. Crimson Dive hits 250 — one of the highest damage ceilings in the game.",
      winCon: "Get Mega Charizard Y ex powered up with 5 energy (Ignition + Moltres ex + natural) and Crimson Dive for 250.",
      energy: ["Fire", "Fire"],
      cards: [
        { name: "Charmander", qty: 2, note: "Use HP 60 Bite version" },
        { name: "Charmeleon", qty: 2, note: "Ignition ability — KEY card" },
        { name: "Mega Charizard Y ex", qty: 2, note: "" },
        { name: "Moltres ex", qty: 1, note: "Energy acceleration" },
        { name: "Victini", qty: 1, note: "Victory Star utility" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Serena", qty: 1, note: "Tutors Mega ex directly" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Giovanni", qty: 1, note: "+10 damage" },
        { name: "Flame Patch", qty: 2, note: "Energy recovery" },
        { name: "Rare Candy", qty: 1, note: "Skip Charmeleon if needed" },
        { name: "Copycat", qty: 1, note: "" },
        { name: "X Speed", qty: 1, note: "Pivot flexibility" },
      ],
    },
    {
      id: "victini",
      name: "Victini + Darmanitan",
      tier: "A",
      type: "Fire",
      typeColor: "#f97316",
      typeBg: "#431407",
      emoji: "⭐",
      rating: 4,
      strategy: "Victory Star lets you reroll all coin flips after seeing results. Darmanitan's Double Smash becomes a near-guaranteed 80 every turn. Tepig's Stoke loads extra energy. Fast, consistent aggro that punishes slow setups.",
      winCon: "Victini on bench → Darmanitan Double Smash → reroll for 2 heads = 80 reliably. Chain KOs before opponent sets up.",
      energy: ["Fire", "Fire"],
      cards: [
        { name: "Victini", qty: 2, note: "Victory Star ability — bench it" },
        { name: "Darumaka", qty: 2, note: "" },
        { name: "Darmanitan", qty: 2, note: "Double Smash 40 per heads" },
        { name: "Tepig", qty: 2, note: "Stoke for energy acceleration" },
        { name: "Moltres ex", qty: 1, note: "Inferno Dance backup" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Flame Patch", qty: 2, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
        { name: "May", qty: 1, note: "" },
      ],
    },
    {
      id: "crobat",
      name: "Crobat Darkness Pivot",
      tier: "A",
      type: "Darkness",
      typeColor: "#a855f7",
      typeBg: "#2e1065",
      emoji: "🦇",
      rating: 4,
      strategy: "Crobat's Surprise Strike hits for 120 the turn it moves from bench to active. Combine with Cyrus to drag damaged bench Pokémon into KO range. Urshifu cleans up anything that survives. Misdreavus' Lead ability finds Supporters every turn.",
      winCon: "Pivot Crobat from bench → 120 damage. Use Cyrus to pull damaged bench targets into active and finish with Crobat or Urshifu.",
      energy: ["Darkness", "Darkness"],
      cards: [
        { name: "Zubat", qty: 1, note: "" },
        { name: "Golbat", qty: 1, note: "" },
        { name: "Crobat", qty: 1, note: "Surprise Strike 120 from bench" },
        { name: "Single Strike Urshifu", qty: 1, note: "Power Blast 110" },
        { name: "Yveltal", qty: 1, note: "Evil Crash disruption" },
        { name: "Misdreavus", qty: 2, note: "Lead ability = free Supporter" },
        { name: "Alolan Persian", qty: 1, note: "" },
        { name: "Giant Cape", qty: 2, note: "Bulk up pivot targets" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Cyrus", qty: 1, note: "Drag damaged bench to active" },
        { name: "Copycat", qty: 1, note: "" },
      ],
    },
    {
      id: "staraptor",
      name: "Staraptor Colorless Blitz",
      tier: "B+",
      type: "Colorless",
      typeColor: "#94a3b8",
      typeBg: "#1e293b",
      emoji: "🦅",
      rating: 3,
      strategy: "Hurricane Wing flips 4 coins at 50 damage each — average 100 damage for 3 Colorless. Bouffalant punishes opponent KOs with 80 revenge damage. Pure Colorless means any energy type works. High variance but high ceiling.",
      winCon: "Evolve to Staraptor fast, Hurricane Wing for ~100 average. Use Bouffalant as revenge attacker after trades.",
      energy: ["Colorless", "Colorless"],
      cards: [
        { name: "Starly", qty: 2, note: "" },
        { name: "Staravia", qty: 1, note: "" },
        { name: "Staraptor", qty: 2, note: "Hurricane Wing — 4 flips × 50" },
        { name: "Bouffalant", qty: 2, note: "Revenge 80 after KO" },
        { name: "Furfrou", qty: 1, note: "Fur Coat -20 damage sponge" },
        { name: "Dodrio", qty: 1, note: "" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
        { name: "Leaf", qty: 1, note: "Retreat cost reduction" },
        { name: "Giant Cape", qty: 1, note: "" },
      ],
    },
  ],
  chase: [
    {
      id: "venusaur",
      name: "Mega Venusaur ex",
      tier: "S",
      type: "Grass",
      typeColor: "#22c55e",
      typeBg: "#052e16",
      emoji: "🌿",
      rating: 5,
      missing: ["1× Ivysaur"],
      haveNote: "Bulbasaur ×5+, Ivysaur ×1 (need ×2), Mega Venusaur ex ×2, Quick-Grow Extract ×4",
      strategy: "Critical Bloom hits 120 AND poisons AND puts them to sleep simultaneously. Breloom's Pre-Dawn Strike does 90 to sleeping Pokémon for 1 energy. Quick-Grow Extract x4 accelerates the Grass evolution line.",
      winCon: "Mega Venusaur ex Critical Bloom → opponent is Poisoned + Asleep → can't attack → repeat.",
      energy: ["Grass", "Grass"],
      cards: [
        { name: "Bulbasaur", qty: 2, note: "" },
        { name: "Ivysaur", qty: 2, note: "⚠️ Have 1, need 1 more" },
        { name: "Mega Venusaur ex", qty: 2, note: "" },
        { name: "Shroomish", qty: 1, note: "Spore — inflict Sleep" },
        { name: "Breloom", qty: 1, note: "Pre-Dawn Strike 90 to sleeping" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Quick-Grow Extract", qty: 2, note: "Grass evolution accelerator" },
        { name: "Serena", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Rare Candy", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
      ],
    },
    {
      id: "incineroar",
      name: "Incineroar ex",
      tier: "A+",
      type: "Fire",
      typeColor: "#ef4444",
      typeBg: "#450a0a",
      emoji: "🐯",
      rating: 5,
      missing: ["1× Incineroar ex"],
      haveNote: "Tepig ×2, Pignite ×4, Incineroar ex ×1",
      strategy: "Incineroar ex's Scar-Charged Smash hits for 140 when it has any damage on it. Fire Fang burns for passive chip. Let it take a hit on purpose, then unleash 140 next turn. Charmeleon Ignition accelerates energy setup.",
      winCon: "Bait 1 hit onto Incineroar ex → Scar-Charged Smash 140 → one-shot most Pokémon in the game.",
      energy: ["Fire", "Fire"],
      cards: [
        { name: "Tepig", qty: 2, note: "" },
        { name: "Pignite", qty: 2, note: "" },
        { name: "Incineroar ex", qty: 2, note: "⚠️ Have 1, need 1 more" },
        { name: "Charmeleon", qty: 1, note: "Ignition free energy on evolve" },
        { name: "Moltres ex", qty: 1, note: "" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Serena", qty: 1, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Flame Patch", qty: 1, note: "" },
        { name: "Rare Candy", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
        { name: "May", qty: 1, note: "" },
      ],
    },
    {
      id: "zygarde",
      name: "Zygarde ex Fighting",
      tier: "A",
      type: "Fighting",
      typeColor: "#eab308",
      typeBg: "#422006",
      emoji: "🐉",
      rating: 4,
      missing: ["1× Zygarde ex"],
      haveNote: "Zygarde 50% Forme ×3, Zygarde ex ×1, Korrina ×2, Arena of Antiquity ×1",
      strategy: "Korrina (+30 vs ex) + Arena of Antiquity (+20 vs ex) stacks to +50 bonus damage against ex Pokémon. Zygarde 50% Forme heals 20 each attack. Zygarde ex Land Laser hits 100 per heads × 2 flips. Most meta decks run ex Pokémon — this punishes all of them.",
      winCon: "Stack Korrina + Arena → attacks deal +50 to ex Pokémon → Zygarde ex Land Laser for up to 200.",
      energy: ["Fighting", "Fighting"],
      cards: [
        { name: "Zygarde 50% Forme", qty: 2, note: "Cell Storm heals 20" },
        { name: "Zygarde ex", qty: 2, note: "⚠️ Have 1, need 1 more" },
        { name: "Cubone", qty: 2, note: "" },
        { name: "Marowak ex", qty: 1, note: "Bonemerang 80+ backup" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Korrina", qty: 2, note: "+30 damage vs ex" },
        { name: "Arena of Antiquity", qty: 1, note: "+20 damage vs ex (stacks!)" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Cyrus", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
      ],
    },
    {
      id: "magnezone",
      name: "Magnezone ex (Clemont Engine)",
      tier: "A",
      type: "Lightning",
      typeColor: "#facc15",
      typeBg: "#1a1a00",
      emoji: "⚡",
      rating: 4,
      missing: ["1× Magnezone ex"],
      haveNote: "Magnemite ×3, Magneton ×3, Magnezone ex ×1, Clemont ×2, Clemont's Backpack ×1, Heliolisk ×2",
      strategy: "Clemont supporter tutors Magneton + Heliolisk + Clemont's Backpack in one go. Clemont's Backpack gives +20 to Magneton and Heliolisk attacks. Magnezone ex Storm Blade hits 130. Heliolisk Thunderbolt hits 120 but discards energy — use strategically.",
      winCon: "Clemont tutors the whole engine. Magnezone ex Storm Blade 130 every turn. Heliolisk Thunderbolt 120 as finisher.",
      energy: ["Lightning", "Lightning"],
      cards: [
        { name: "Magnemite", qty: 2, note: "" },
        { name: "Magneton", qty: 2, note: "Spark hits bench" },
        { name: "Magnezone ex", qty: 2, note: "⚠️ Have 1, need 1 more" },
        { name: "Heliolisk", qty: 2, note: "Thunderbolt 120 finisher" },
        { name: "Poké Ball", qty: 2, note: "" },
        { name: "Professor's Research", qty: 2, note: "" },
        { name: "Clemont", qty: 2, note: "Tutors entire engine" },
        { name: "Clemont's Backpack", qty: 1, note: "+20 to Magneton & Heliolisk" },
        { name: "Rare Candy", qty: 1, note: "Skip to Magnezone" },
        { name: "Sabrina", qty: 1, note: "" },
        { name: "Giovanni", qty: 1, note: "" },
        { name: "Copycat", qty: 1, note: "" },
      ],
    },
  ],
};

const PACK_RECS = [
  { priority: 1, card: "Ivysaur", deck: "Mega Venusaur ex", note: "Grass-type packs from the Mega Evolution set" },
  { priority: 2, card: "Incineroar ex", deck: "Incineroar ex", note: "Fire-type packs from the Scarlet/Violet era set" },
  { priority: 3, card: "Zygarde ex", deck: "Zygarde ex Fighting", note: "Zygarde packs (special set — check Wonder Pick first)" },
  { priority: 4, card: "Magnezone ex", deck: "Magnezone ex", note: "Lightning packs from Genetic Apex (Pikachu pack)" },
  { priority: 5, card: "Marowak ex", deck: "Zygarde Fighting variant", note: "Same set as Zygarde ex" },
];

const tierColors = {
  S: { bg: "#fbbf24", text: "#000" },
  "A+": { bg: "#f97316", text: "#fff" },
  A: { bg: "#a855f7", text: "#fff" },
  "B+": { bg: "#3b82f6", text: "#fff" },
};

function StarRating({ count }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {[1,2,3,4,5].map(i => (
        <span key={i} style={{ color: i <= count ? "#fbbf24" : "#374151", fontSize: 12 }}>★</span>
      ))}
    </div>
  );
}

function TypeBadge({ type, color }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "2px 8px",
      borderRadius: 99, border: `1px solid ${color}40`,
      color: color, background: `${color}15`, letterSpacing: "0.05em"
    }}>{type.toUpperCase()}</span>
  );
}

function TierBadge({ tier }) {
  const c = tierColors[tier] || { bg: "#4b5563", text: "#fff" };
  return (
    <span style={{
      fontSize: 11, fontWeight: 900, padding: "2px 8px",
      borderRadius: 4, background: c.bg, color: c.text,
      letterSpacing: "0.1em", fontFamily: "monospace"
    }}>{tier}</span>
  );
}

function DeckCard({ deck, showMissing }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      background: "linear-gradient(135deg, #111827 0%, #1f2937 100%)",
      border: `1px solid ${deck.typeColor}30`,
      borderRadius: 12,
      overflow: "hidden",
      marginBottom: 12,
      boxShadow: open ? `0 0 20px ${deck.typeColor}20` : "none",
      transition: "box-shadow 0.3s ease",
    }}>
      {/* Header */}
      <div
        onClick={() => setOpen(!open)}
        style={{
          padding: "14px 16px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 12,
          userSelect: "none",
        }}
      >
        <span style={{ fontSize: 24 }}>{deck.emoji}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ color: "#f9fafb", fontWeight: 700, fontSize: 15, fontFamily: "'Georgia', serif" }}>
              {deck.name}
            </span>
            <TierBadge tier={deck.tier} />
            <TypeBadge type={deck.type} color={deck.typeColor} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <StarRating count={deck.rating} />
            {showMissing && (
              <span style={{ fontSize: 11, color: "#f59e0b", fontWeight: 600 }}>
                ⚠️ {deck.missing?.join(", ")}
              </span>
            )}
          </div>
        </div>
        <span style={{ color: "#6b7280", fontSize: 18, transition: "transform 0.2s", transform: open ? "rotate(180deg)" : "none" }}>▾</span>
      </div>

      {/* Expanded */}
      {open && (
        <div style={{ borderTop: `1px solid ${deck.typeColor}20`, padding: 16 }}>
          {showMissing && deck.haveNote && (
            <div style={{
              background: "#92400e20", border: "1px solid #f59e0b40",
              borderRadius: 8, padding: "8px 12px", marginBottom: 12, fontSize: 12, color: "#fcd34d"
            }}>
              📦 <strong>Have:</strong> {deck.haveNote}
            </div>
          )}

          <p style={{ color: "#9ca3af", fontSize: 13, lineHeight: 1.6, margin: "0 0 12px" }}>
            {deck.strategy}
          </p>

          <div style={{
            background: `${deck.typeColor}10`, border: `1px solid ${deck.typeColor}25`,
            borderRadius: 8, padding: "8px 12px", marginBottom: 14, fontSize: 12
          }}>
            <span style={{ color: deck.typeColor, fontWeight: 700 }}>WIN CON: </span>
            <span style={{ color: "#d1d5db" }}>{deck.winCon}</span>
          </div>

          {/* Card list */}
          <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 700, marginBottom: 6, letterSpacing: "0.08em" }}>
            20-CARD LIST
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px" }}>
            {deck.cards.map((c, i) => (
              <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 6, padding: "3px 0", borderBottom: "1px solid #ffffff08" }}>
                <span style={{
                  minWidth: 20, color: deck.typeColor, fontWeight: 700, fontSize: 12, fontFamily: "monospace"
                }}>{c.qty}×</span>
                <span style={{ color: c.note?.includes("⚠️") ? "#f59e0b" : "#e5e7eb", fontSize: 12, flex: 1 }}>{c.name}</span>
                {c.note && !c.note.includes("⚠️") && (
                  <span style={{ color: "#4b5563", fontSize: 10, fontStyle: "italic" }}>{c.note}</span>
                )}
              </div>
            ))}
          </div>

          {/* Energy */}
          <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 11, color: "#6b7280" }}>ENERGY:</span>
            {deck.energy.map((e, i) => (
              <span key={i} style={{ fontSize: 11, color: deck.typeColor, fontWeight: 700 }}>{e}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DeckGuide() {
  const [tab, setTab] = useState("buildable");

  return (
    <div style={{
      minHeight: "100vh",
      background: "#030712",
      padding: "0 0 40px",
      fontFamily: "'system-ui', sans-serif",
    }}>
      {/* Header */}
      <div style={{
        background: "linear-gradient(180deg, #1a0a00 0%, #030712 100%)",
        padding: "24px 16px 20px",
        borderBottom: "1px solid #1f2937",
        textAlign: "center",
      }}>
        <div style={{ fontSize: 28, marginBottom: 4 }}>🃏</div>
        <h1 style={{
          color: "#f9fafb", margin: 0, fontSize: 20, fontWeight: 900,
          fontFamily: "'Georgia', serif", letterSpacing: "-0.02em"
        }}>Deck Recommendations</h1>
        <p style={{ color: "#6b7280", margin: "4px 0 0", fontSize: 12 }}>
          Based on your 380-card collection
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", padding: "12px 16px 0", gap: 8 }}>
        {[
          { id: "buildable", label: "✅ Build Now", sub: "4 decks" },
          { id: "chase", label: "🎯 1 Card Away", sub: "4 decks" },
          { id: "packs", label: "📦 Pack Priority", sub: "" },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            flex: 1, padding: "10px 4px", borderRadius: 8, border: "none", cursor: "pointer",
            background: tab === t.id ? "#1f2937" : "transparent",
            borderBottom: tab === t.id ? "2px solid #f59e0b" : "2px solid transparent",
            color: tab === t.id ? "#f9fafb" : "#6b7280",
            fontSize: 12, fontWeight: 700, transition: "all 0.15s"
          }}>
            {t.label}
            {t.sub && <div style={{ fontSize: 10, fontWeight: 400, color: "#4b5563" }}>{t.sub}</div>}
          </button>
        ))}
      </div>

      <div style={{ padding: "16px 16px 0" }}>
        {tab === "buildable" && (
          <div>
            <p style={{ color: "#4b5563", fontSize: 12, margin: "0 0 14px", fontStyle: "italic" }}>
              All cards in hand. Tap a deck to see the full list.
            </p>
            {DECKS.buildable.map(d => <DeckCard key={d.id} deck={d} showMissing={false} />)}
          </div>
        )}

        {tab === "chase" && (
          <div>
            <p style={{ color: "#4b5563", fontSize: 12, margin: "0 0 14px", fontStyle: "italic" }}>
              Each deck needs exactly 1 card. Strongest meta options.
            </p>
            {DECKS.chase.map(d => <DeckCard key={d.id} deck={d} showMissing={true} />)}
          </div>
        )}

        {tab === "packs" && (
          <div>
            <p style={{ color: "#4b5563", fontSize: 12, margin: "0 0 14px", fontStyle: "italic" }}>
              Open in this order to unlock the most decks fastest.
            </p>
            {PACK_RECS.map((p, i) => (
              <div key={i} style={{
                background: "#111827", border: "1px solid #1f2937",
                borderRadius: 10, padding: "12px 14px", marginBottom: 10,
                display: "flex", gap: 12, alignItems: "flex-start"
              }}>
                <div style={{
                  minWidth: 28, height: 28, borderRadius: 99, background: "#1f2937",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: "#fbbf24", fontWeight: 900, fontSize: 13
                }}>#{p.priority}</div>
                <div>
                  <div style={{ color: "#f9fafb", fontWeight: 700, fontSize: 14 }}>{p.card}</div>
                  <div style={{ color: "#6b7280", fontSize: 11, marginTop: 2 }}>Unlocks: <span style={{ color: "#a78bfa" }}>{p.deck}</span></div>
                  <div style={{ color: "#4b5563", fontSize: 11, marginTop: 2 }}>📦 {p.note}</div>
                </div>
              </div>
            ))}

            <div style={{
              background: "#0f172a", border: "1px solid #1f2937",
              borderRadius: 10, padding: "14px 16px", marginTop: 16
            }}>
              <div style={{ color: "#fbbf24", fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
                💡 Wonder Pick Strategy
              </div>
              <p style={{ color: "#6b7280", fontSize: 12, margin: 0, lineHeight: 1.7 }}>
                Ivysaur and Incineroar ex are your best Wonder Pick targets — single card unlocks a full S/A+ tier deck. 
                Set alerts for both. Zygarde ex may appear in a special event pack — check the shop rotation weekly.
                Your Serena ×1 already tutors Mega Evolution ex cards, so Mega Charizard is viable immediately.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
