<!-- wygenerowane przez narzedzia/generuj_figury.py; nie edytować ręcznie -->

```{=html}
<svg viewBox="0 0 1180 560" class="funsearch-kod" role="img" aria-label="Funkcja priority: startowa, napisana przez ludzi, zwraca zawsze 0 i daje 256 punktów; znaleziona przez model językowy ma 33 wiersze i daje 512 punktów">
<text x="590" y="34" class="szkielet-opis">przepis ludzi: bierz punkty od najwyższej oceny <tspan class="fn">priority</tspan>, póki nie ma prostej</text>
<text x="185" y="100" class="kto" fill="#1f4e79">start · napisali ludzie</text>
<rect x="10" y="130" width="350" height="90" rx="8" class="kod-tlo" stroke="#1f4e79"/>
<text x="24" y="166" class="kod" xml:space="preserve"><tspan class="kw">def</tspan> <tspan class="fn">priority</tspan>(el, n):</text>
<text x="24" y="198" class="kod" xml:space="preserve">  <tspan class="kw">return</tspan> 0.0</text>
<text x="185" y="298" class="wynik" fill="#1f4e79">256</text><text x="185" y="334" class="podpis">punktów bez prostej</text>
<g class="znaleziona"><text x="635" y="100" class="kto" fill="#a65a17">znaleziona · napisał model</text>
<rect x="400" y="130" width="470" height="410" rx="8" class="kod-tlo" stroke="#a65a17"/>
<text x="414" y="166" class="kod" xml:space="preserve"><tspan class="kw">def</tspan> <tspan class="fn">priority</tspan>(el, n):</text>
<text x="414" y="198" class="kod" xml:space="preserve">  score = n</text>
<text x="414" y="230" class="kod" xml:space="preserve">  in_el = 0</text>
<text x="414" y="262" class="kod" xml:space="preserve">  el_count = el.count(0)</text>
<text x="414" y="294" class="kod" xml:space="preserve">  <tspan class="kw">if</tspan> el_count == 0:</text>
<text x="414" y="326" class="kod" xml:space="preserve">    score += n**2</text>
<rect x="404" y="334" width="462" height="32" class="pasek-symetrii"/>
<text x="414" y="358" class="kod" xml:space="preserve">    <tspan class="kw">if</tspan> el[1] == el[-1]:</text>
<text x="414" y="390" class="kod" xml:space="preserve">      score *= 1.5</text>
<rect x="404" y="398" width="462" height="32" class="pasek-symetrii"/>
<text x="414" y="422" class="kod" xml:space="preserve">    <tspan class="kw">if</tspan> el[2] == el[-2]:</text>
<text x="414" y="454" class="kod" xml:space="preserve">      score *= 1.5</text>
<text x="414" y="486" class="pominiete">⋮ 22 wiersze pominięte</text>
<text x="414" y="518" class="kod" xml:space="preserve">  <tspan class="kw">return</tspan> score</text>
<text x="1025" y="206" class="wynik" fill="#a65a17">512</text><text x="1025" y="242" class="podpis">punktów bez prostej</text></g>
<g class="symetria-opis"><text x="1025" y="358" class="opis-symetrii"><tspan class="kod">el[i] == el[-i]</tspan></text><text x="1025" y="398" class="podpis">i-ta współrzędna</text><text x="1025" y="428" class="podpis">i i-ta od końca:</text><text x="1025" y="458" class="podpis">widać symetrię</text><text x="1025" y="488" class="podpis">rozwiązania</text></g>
</svg>
```
