#!/usr/bin/env python3

# Imports
import pandas as pd
import numpy as np
import sys

#Helper functions
def genAF():
    return np.round(np.random.uniform(0,1), 5)

def genRsquared():
    return np.round(np.random.uniform(0,1), 5)

def genMAF(AF):
    delta = np.round((1 - AF), 3)
    if delta > 0.5:
        return AF
    return delta

def genType():
    mapType = {0:"IMPUTED", 1:"TYPED"}
    return mapType[np.random.choice([0,1])]

def genAlleles():
    bases = ['A', 'T', 'C', 'G']
    refAllele = np.random.choice(bases)
    bases.remove(refAllele)
    altAllele = np.random.choice(bases)
    return (refAllele, altAllele)

def genGT():
    ref = np.random.choice([0,1])
    alt = np.random.choice([0,1])
    return f"{ref}|{alt}"

def genDS():
    return np.round(np.random.uniform(0, 1), 3)

def genHDS():
    return "{},{}".format(np.round(np.random.uniform(0, 1), 3), np.round(np.random.uniform(0, 1), 3))

def genGP():
    num1 = np.round(np.random.uniform(0, 1), 3)
    num2 = np.round(np.random.uniform(0, (1-num1)), 3)
    num3 = np.round(1 - (num1+num2), 3)
    return f"{num1},{num2},{num3}"

def genSample():
    return ":".join([genGT(), str(genDS()), genHDS(), genGP()])

# Create VCF for given chromosome
chromo = sys.argv[1]
Nsamples = 100
Nsnps = {
    "1":742931,
    "2":821107,
    "3":701135,
    "4":711152,
    "5":636445,
    "6":647058,
    "7":561973,
    "8":547425,
    "9":417166,
    "10":494306,
    "11":487391,
    "12":457103,
    "13":359902,
    "14":312209,
    "15":266501,
    "16":291464,
    "17":243067,
    "18":270895,
    "19":190216,
    "20":211777,
    "21":127529,
    "22":122079,
    "X":10079,
    "Y":6009,
    "M":4009 }

if chromo == "1":
    with open(f"chr{chromo}.vcf", 'w') as outf:
        vcfColumns = ['#CHROM','POS','ID','REF','ALT','QUAL','FILTER','INFO','FORMAT'] + ["SA"+f"{i}".zfill(3) for i in range(1, Nsamples+1)]
        print("\t".join(vcfColumns), file=outf)

with open(f"chr{chromo}.vcf", 'a') as outf:
    for pos in range(10000, 10000+Nsnps[chromo]+1):
        ref, alt = genAlleles()
        AF = genAF()
        MAF = genMAF(AF)
        row = [ f"chr{chromo}",
                str(pos),
                f"{chromo}:{pos}:{ref}:{alt}",
                ref,
                alt,
                '.',
                'PASS',
                f"AF={AF}:{genType()}:MAF={MAF}:R2={genRsquared()}",
                "GT:DS:HDS:GP"
                ]
        for _ in range(Nsamples):
            row.append(genSample())
        print("\t".join(row), file=outf)

