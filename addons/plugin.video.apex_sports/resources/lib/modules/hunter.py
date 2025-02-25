# -*- coding: UTF-8 -*-

def _0xe35c(d, e, f):# {
    g = list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/")
    h = g[0:e]
    i = g[0:f]
    listad = list(d)[::-1]
    def redux(listad):
        j=0
        for c in range(len(listad)):
            b = listad[c]
            if b in h:
                j+=h.index(b)*(e**c)
        return j  
    j=redux(listad)
    k=''
    while j > 0:
        k = i[int(j % f)] + k;
        j = (j - (j % f)) / f

    return int(k) if k else 0

def dehunt (h, u, n, t, e, r):# {
    r = "";
    i = 0
    while i < len(h):
        s =''
        while h[i] != n[e]:
            s += h[i];
            i+=1
        for j in range(len(n)):
            s = s.replace(n[j], str(j))
        r +=chr(_0xe35c(s, e, 10) - t)
        i+=1
    return r