#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Full-batch UCR test generation.
# qwenlocal defaults to a local OpenAI-compatible endpoint.

INPUT="$ROOT_DIR/dataset/classification/UCRArchive_2018"
OUTDIR="$ROOT_DIR/gen_tst_dataset/ucr/test_shards"
mkdir -p "$OUTDIR"

run_one () {
  local name="$1"
  python -m ts_cap.cli \
    --dataset ucr2018 \
    --input "$INPUT" \
    --ucr_name "$name" \
    --output "${OUTDIR}/ucr_${name}_test.jsonl" \
    --task classification \
    --ucr_split test \
    --ucr_label_semantics readme \
    --llm_provider qwenlocal
}

# =========================
# 1) Medical & Biological
# =========================
run_one ECG200
run_one ECG5000
run_one TwoLeadECG
run_one ECGFiveDays
#run_one CinCECGTorso
#run_one NonInvasiveFetalECGThorax1
run_one NonInvasiveFetalECGThorax2
run_one MedicalImages
run_one SemgHandSubjectCh2
run_one SemgHandMovementCh2
run_one SemgHandGenderCh2
run_one EOGHorizontalSignal
run_one EOGVerticalSignal
run_one PigAirwayPressure
run_one PigArtPressure
run_one PigCVP
run_one Worms
run_one WormsTwoClass
run_one Fungi
run_one HandOutlines
# run_one PhalangesOutlinesCorrect

# =========================
# 2) Power & Energy
# =========================
# run_one ItalyPowerDemand
# run_one PowerCons
run_one RefrigerationDevices
run_one ElectricDevices
# run_one LargeKitchenAppliances
run_one SmallKitchenAppliances
run_one Computers
run_one ScreenType
run_one FreezerRegularTrain
run_one FreezerSmallTrain
run_one HouseTwenty
run_one ACSF1
run_one PLAID

# =========================
# 3) Image & Shape
# =========================
run_one MixedShapesRegularTrain
run_one MixedShapesSmallTrain
run_one ShapesAll
run_one SwedishLeaf
run_one OSULeaf
run_one FaceAll
run_one FacesUCR
run_one FaceFour
run_one Yoga
run_one Fish
run_one Herring
run_one ArrowHead
run_one BeetleFly
run_one BirdChicken
# run_one Adiac
run_one DiatomSizeReduction
run_one FiftyWords
run_one WordSynonyms
run_one Symbols
run_one Plane
run_one Car

# =========================
# 4) Motion & Gesture
# =========================
# run_one GunPoint
run_one GunPointAgeSpan
run_one GunPointGender
# run_one CricketX
run_one CricketY
run_one CricketZ
run_one UWaveGestureLibraryX
run_one UWaveGestureLibraryY
run_one UWaveGestureLibraryZ
run_one UWaveGestureLibraryAll
run_one Haptics
run_one ToeSegmentation1
run_one ToeSegmentation2
run_one InlineSkate

# =========================
# 5) Spectrograph & Food Safety
# =========================
run_one Beef
# run_one Meat
# run_one Ham
run_one OliveOil
run_one Coffee
run_one Strawberry
run_one Wine
run_one EthanolLevel
run_one Rock

# =========================
# 6) Sensor, Traffic & Environment
# =========================
# run_one Chinatown
# run_one MelbournePedestrian
run_one DodgerLoopDay
run_one DodgerLoopGame
run_one DodgerLoopWeekend
run_one FordA
run_one FordB
run_one Wafer
run_one ChlorineConcentration
# run_one Earthquakes
run_one StarLightCurves
# run_one Crop
run_one InsectWingbeatSound
run_one Lightning2
# run_one Lightning7
run_one MoteStrain
run_one SonyAIBORobotSurface1
run_one SonyAIBORobotSurface2

# =========================
# 7) Synthetic / Simulated
# =========================
run_one SyntheticControl
run_one CBF
run_one TwoPatterns
run_one Mallat
run_one Trace
run_one UMD
# run_one SmoothSubspace
run_one BME
run_one ShapeletSim
