# Verify that no dummy of any layer lands inside any nofill region.
# The requirement is stack-wide: the union of every nofill layer must be free of
# dummy on every filler layer, not merely on its own layer.
G = "/project/ihp_sg13g2/mpw202609_teg_openpdk/verification/LNA2609_nofill/gds/runs/2026-09-10_161359_fill/LNA2609.gds"
ly = RBA::Layout::new; ly.read(G); top = ly.top_cell; DBU = ly.dbu
def region(ly, top, l, d)
  r = RBA::Region::new(top.begin_shapes_rec(ly.layer(l, d))); r.merged_semantics = true; r
end

NOFILL = [[1,23],[5,23],[8,23],[10,23],[30,23],[50,23],[67,23],[126,23],[134,23],[160,0]]
FILLER = [["Activ",1,22],["GatPoly",5,22],["Metal1",8,22],["Metal2",10,22],
          ["Metal3",30,22],["Metal4",50,22],["Metal5",67,22],
          ["TopMetal1",126,22],["TopMetal2",134,22]]

nf = RBA::Region::new
NOFILL.each { |l,d| nf += region(ly, top, l, d) }
nf.merge
puts "nofill union   %d polygons, %.1f um2" % [nf.count, nf.area*DBU*DBU]
puts
puts "  STACK-WIDE NOFILL CHECK"
bad = 0
FILLER.each do |n,l,d|
  f = region(ly, top, l, d); f.merge
  hit = f & nf
  a = hit.area * DBU * DBU
  bad += hit.count
  printf("    %-10s %3d/%-3d  filler %10.1f um2   inside nofill: %d polygons, %.4f um2  %s\n",
         n, l, d, f.area*DBU*DBU, hit.count, a, hit.is_empty? ? "CLEAN" : "VIOLATION")
end
puts
puts bad == 0 ? "  RESULT: clean, no dummy of any layer touches any nofill region" :
                "  RESULT: #{bad} dummy polygons intrude into nofill regions"
puts
puts "  also check the dummy stays off the sealring"
seal = region(ly, top, 39, 0); seal.merge
FILLER.each do |n,l,d|
  f = region(ly, top, l, d); f.merge
  hit = f & seal
  printf("    %-10s overlaps sealring: %d polygons, %.4f um2\n", n, hit.count, hit.area*DBU*DBU)
end
