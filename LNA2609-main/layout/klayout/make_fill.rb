# ---------------------------------------------------------------------------
# Dummy fill generator for the IHP SG13G2 open MPW top cell.
#
# The original GDS is never modified.  A new file is written beside this script
# and every dummy shape lives in a cell whose name starts with FILL_, so the
# fill can be removed again by deleting those cells.
#
# Rule values were read out of the open PDK deck rather than assumed:
#   AFil.a  max Activ:filler width       5.00     AFil.a1 min width  1.00
#   AFil.b  min Activ:filler space       1.00
#   GFil.a  max GatPoly:filler width     5.00     GFil.b  min width  0.70
#   GFil.c  min GatPoly:filler space     0.80     GFil.f  to TRANS   1.10
#   GFil.j  GatPoly:filler must enclose Activ:filler by 0.18 where the two
#           overlap, so this script keeps them disjoint and the rule idles.
#   MnFil.a1 min Metaln:filler width     1.00     MnFil.b min space  0.42
#   MnFil.d  min Metaln:filler to TRANS  1.00
#   Act.b / Gat.b / M1.b are (drawing + filler) space rules at 0.21 / 0.18 /
#           0.18, so the clearance kept from drawn geometry is the larger of
#           the filler space rule and that value.
#
# Density is measured over edgeseal_bound (39/4), a single 2999424 um2 polygon,
# because prBoundary (189/0) is empty here.  Metal density subtracts the slit
# layers, so fill is kept out of the slits as well.
#
# Activ and GatPoly share one grid.  Placing them in two passes does not work,
# because the first pass leaves channels too narrow for the second pass's pitch
# cell and the second layer then lands at under one percent.
# ---------------------------------------------------------------------------

SRC = "/project/ihp_sg13g2/mpw202609_teg_openpdk/designlib/teg/LNA2609_nofill/LNA2609_nofill.gds"
# The filled cell is a cell, so it lives in designlib/teg/ under its own name like every
# other cell in this project. Owner instruction 2026-09-15.
FILLED = "LNA2609"
DST = "/project/ihp_sg13g2/mpw202609_teg_openpdk/designlib/teg/#{FILLED}/#{FILLED}.gds"

ly = RBA::Layout::new
ly.read(SRC)
top = ly.top_cell
DBU = ly.dbu
U = lambda { |v| (v / DBU).round }
# Every drawn dimension and every raster pitch has to land on the 5 nm
# manufacturing grid, which rule 3.1 <layer>_Offgrid enforces.  Rounding to the
# database unit alone is not enough, because the database unit here is 1 nm.
GRID = 5
S = lambda { |v| ((v / DBU) / GRID.to_f).round * GRID }
# fill_region anchors its raster where it likes, so the instances it creates are
# snapped afterwards.  The shift is at most 2 nm and cannot eat into a clearance.
def snap_fill_instances(ly, top, grid)
  moved = 0
  top.each_inst do |i|
    next unless ly.cell(i.cell_index).name.start_with?("FILL_")
    t = i.trans
    dx = (t.disp.x.to_f / grid).round * grid
    dy = (t.disp.y.to_f / grid).round * grid
    next if dx == t.disp.x && dy == t.disp.y
    ci = i.cell_inst
    ci.trans = RBA::Trans::new(t.rot, RBA::Vector::new(dx, dy))
    i.cell_inst = ci
    moved += 1
  end
  moved
end

def region(ly, top, l, d)
  r = RBA::Region::new(top.begin_shapes_rec(ly.layer(l, d)))
  r.merged_semantics = true
  r
end

chip = region(ly, top, 39, 4); chip.merge
CA = chip.area * DBU * DBU
puts "chip area for density    %.1f um2" % CA

nofill = RBA::Region::new
[[1,23],[5,23],[8,23],[10,23],[30,23],[50,23],[67,23],[126,23],[134,23],[160,0]].each do |l,d|
  nofill += region(ly, top, l, d)
end
nofill.merge
puts "nofill union             %.1f um2 in %d polygons" % [nofill.area*DBU*DBU, nofill.count]

seal  = region(ly, top, 39, 0); seal.merge
trans = region(ly, top, 26, 0); trans.merge
inner = chip - seal.sized(S.call(3.0)); inner.merge
puts "area inside the seal     %.1f um2" % (inner.area*DBU*DBU)
puts

# ===========================================================================
# Pass 1: Activ and GatPoly on one shared grid.
# ===========================================================================
activ_drw = region(ly, top, 1, 0)
activ_msk = region(ly, top, 1, 20)
gat_drw   = region(ly, top, 5, 0)
act_cur = (activ_drw + activ_msk); act_cur.merge
gat_cur = gat_drw.dup;             gat_cur.merge
act_a0 = act_cur.area * DBU * DBU
gat_a0 = gat_cur.area * DBU * DBU

feol_block = act_cur.sized(S.call(1.2)) + gat_drw.sized(S.call(1.0)) +
             nofill + trans.sized(S.call(1.5))
feol_block.merge
feol_av = inner - feol_block; feol_av.merge
AV = feol_av.area * DBU * DBU

ACT_T = 0.40   # Activ target, rule window is 35 to 55 percent
GAT_T = 0.18   # GatPoly target, rule minimum is 15 percent
P     = 6.0   # already a multiple of the 5 nm grid    # shared pitch
LOSS  = 1.25   # tiles that fill_region drops where a pitch cell does not fit

need_a = ACT_T * CA - act_a0
need_g = GAT_T * CA - gat_a0
a = ((P * Math.sqrt([need_a * LOSS / AV, 0.72].min)) / DBU / GRID).round * GRID * DBU   # Activ square side, snapped to the grid
# GatPoly is an L in the strip the Activ square leaves free.  Solving
# 2*L*t - t^2 = area_per_cell for the L thickness t, with L the arm length.
gl = P - 0.9
ga = [need_g * LOSS / AV, 0.45].min * P * P
t  = ((gl - Math.sqrt([gl*gl - ga, 0.0].max)) / DBU / GRID).round * GRID * DBU
t  = 0.70 if t < 0.70

# GFil.b and GFil.c, the minimum GatPoly:filler width of 0.70 um and the minimum space of
# 0.80 um. Both are settled by building the tile and measuring it, not by deriving the space
# from a and t. Two hand derivations of that space were attempted on 2026-09-15 and both were
# wrong, the first by taking a cap on t alone to be sufficient and the second by dropping the
# 0.15 um offset of yb, so the derivation is abandoned in favour of the geometry itself.
GFIL_B = 0.70
GFIL_C = 0.80

# build one tile's GatPoly at a given a and t, in the coordinates of one pitch cell
def gat_tile(a, t, p, s_, dbu)
  h  = p / 2.0
  yb = -h + a + 0.15
  r  = RBA::Region::new
  r.insert(RBA::Box::new(s_.call(-h+0.45), s_.call(yb), s_.call(h-0.45), s_.call(yb+t)))
  r.insert(RBA::Box::new(s_.call(yb), s_.call(-h+0.45), s_.call(yb+t), s_.call(yb)))
  r.merge
  r
end

# the space to the neighbour is measured, by putting a copy one pitch away in each direction
def tile_space(a, t, p, s_, dbu)
  one = gat_tile(a, t, p, s_, dbu)
  pu  = (p / dbu).round
  both = one.dup
  [[pu, 0], [0, pu], [pu, pu]].each do |dx, dy|
    both += one.transformed(RBA::Trans::new(RBA::Vector::new(dx, dy)))
  end
  ec = both.space_check(10 ** 7, false, RBA::Region::Euclidian, nil, nil, nil)
  return 1.0e9 if ec.count == 0
  ec.each.map { |e| e.distance }.min * dbu
end

tries = 0
loop do
  sp = tile_space(a, t, P, S, DBU)
  br = gat_tile(a, t, P, S, DBU).width_check((GFIL_B / DBU).round).count
  break if sp >= GFIL_C - 1e-9 && br == 0
  tries += 1
  raise "the GatPoly tile cannot be made to pass GFil.b and GFil.c" if tries > 400
  # The reduction comes out of both dimensions in turn rather than out of one of them.
  # Activ area goes as a squared and GatPoly area goes as t, so spending the whole reduction
  # on t empties GatPoly first: taking it all from the L on 2026-09-15 dropped GatPoly from
  # 20.88 percent to 12.20 and put it under its own 15 percent minimum. Alternating keeps both
  # figures in the middle of their windows instead of pinning one against a limit.
  # The L still stops at GFil.b's 0.70, below which the shape itself would be illegal.
  if tries.odd? && a > 3.0
    a = ((a - 0.005) / DBU / GRID).round * GRID * DBU
  elsif t - 0.005 >= GFIL_B
    t = ((t - 0.005) / DBU / GRID).round * GRID * DBU
  else
    a = ((a - 0.005) / DBU / GRID).round * GRID * DBU
  end
end
printf("GatPoly tile settled     %d step(s)   Activ %.3f  L thickness %.3f  measured space %.3f um (GFil.c asks %.2f)\n",
       tries, a, t, tile_space(a, t, P, S, DBU), GFIL_C)

fc = ly.create_cell("FILL_FEOL")
al = ly.layer(1, 22)
gll = ly.layer(5, 22)
h = P / 2.0
x0 = -h                       # Activ square sits in the lower left of the cell
fc.shapes(al).insert(RBA::Box::new(S.call(x0), S.call(x0), S.call(x0+a), S.call(x0+a)))
yb = x0 + a + 0.15            # GatPoly keeps 0.15 clear of the Activ square
fc.shapes(gll).insert(RBA::Box::new(S.call(-h+0.45), S.call(yb), S.call(h-0.45), S.call(yb+t)))
fc.shapes(gll).insert(RBA::Box::new(S.call(yb), S.call(-h+0.45), S.call(yb+t), S.call(yb)))
pbox = RBA::Box::new(S.call(-h), S.call(-h), S.call(h), S.call(h))
top.fill_region(feol_av, fc.cell_index, pbox, RBA::Point::new(0, 0))

af = region(ly, top, 1, 22);  af.merge
gf = region(ly, top, 5, 22);  gf.merge
printf("  Activ    %6.2f%% -> %6.2f%%   fill %.1f um2\n",
       act_a0/CA*100, (act_cur + af).merged.area*DBU*DBU/CA*100, af.area*DBU*DBU)
printf("  GatPoly  %6.2f%% -> %6.2f%%   fill %.1f um2\n",
       gat_a0/CA*100, (gat_cur + gf).merged.area*DBU*DBU/CA*100, gf.area*DBU*DBU)
puts

# ===========================================================================
# Pass 2: the metal layers, each on its own grid.
# ===========================================================================
[["Metal1",8],["Metal2",10],["Metal3",30],["Metal4",50],["Metal5",67]].each do |name, l|
  drw  = region(ly, top, l, 0);  drw.merge
  slit = region(ly, top, l, 24); slit.merge
  cur  = drw - slit; cur.merge                 # density subtracts the slits
  cur_a = cur.area * DBU * DBU

  block = drw.sized(S.call(0.6)) + slit + nofill + trans.sized(S.call(1.2))
  block.merge
  av = inner - block; av.merge
  av_a = av.area * DBU * DBU

  need = 0.42 * CA - cur_a
  if need <= 0
    printf("%-8s %6.2f%% already meets the minimum, no fill placed\n", name, cur_a/CA*100)
    next
  end
  tile  = 2.0
  local = [need * LOSS / av_a, 0.70].min
  pitch = [tile / Math.sqrt(local), tile + 0.6].max
  pitch = (pitch / DBU / GRID).round * GRID * DBU   # keep the raster on grid

  fcm = ly.create_cell("FILL_#{name}")
  fl  = ly.layer(l, 22)
  hh  = S.call(tile / 2.0)
  fcm.shapes(fl).insert(RBA::Box::new(-hh, -hh, hh, hh))
  ph = S.call(pitch / 2.0)
  pb = RBA::Box::new(-ph, -ph, ph, ph)
  top.fill_region(av, fcm.cell_index, pb, RBA::Point::new(0, 0))

  fil = region(ly, top, l, 22); fil.merge
  newd = ((drw + fil) - slit).merged.area * DBU * DBU
  printf("%-8s %6.2f%%  avail %9.1f  pitch %5.2f  fill %9.1f um2  -> %6.2f%%\n",
         name, cur_a/CA*100, av_a, pitch, fil.area*DBU*DBU, newd/CA*100)
end

moved = snap_fill_instances(ly, top, GRID)
puts "snapped %d fill instances onto the %d nm grid" % [moved, GRID]
# The top cell is renamed only now, so every line printed above names the cell the numbers
# were actually measured on. Renaming leaves the cell index untouched, so nothing placed
# during the fill moves.
top.name = FILLED
require "fileutils"
FileUtils.mkdir_p(File.dirname(DST))
ly.write(DST)
puts
puts "written  #{DST}"
