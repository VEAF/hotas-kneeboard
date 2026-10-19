<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Box } from '../lib/types'
import { inputName } from '../render/inputs'
import { addInput, boxOf, clamp, editor, remember, round, setBox, type Selection } from './state'
import { sortedKeys } from './catalog'

const props = defineProps<{ placing: string | null }>()
const emit = defineEmits<{ placed: [] }>()

const svg = ref<SVGSVGElement | null>(null)
const draft = computed(() => editor.draft!)
const keys = computed(() => sortedKeys(Object.keys(draft.value.inputs)))
const MIN_BOX: [number, number] = [24, 10]

interface Drag {
  sel: Selection
  mode: 'move' | 'resize'
  start: [number, number]
  box: Box | null
  anchor: [number, number] | null
  remembered: boolean
}
let drag: Drag | null = null
let splitDrag: { index: number; start: number; from: number; remembered: boolean } | null = null

function startSplitDrag(event: PointerEvent, index: number) {
  if (event.button !== 0) return
  event.stopPropagation()
  splitDrag = { index, start: point(event)[0], from: draft.value.split_at[index], remembered: false }
  ;(event.currentTarget as Element).setPointerCapture(event.pointerId)
}

function point(event: MouseEvent | DragEvent): [number, number] {
  const matrix = svg.value!.getScreenCTM()!.inverse()
  const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix)
  return [clamp(p.x, 0, draft.value.size[0]), clamp(p.y, 0, draft.value.size[1])]
}

function isSelected(key: string, part: 'box' | 'anchor', index = 0): boolean {
  const s = editor.selection
  return !!s && s.key === key && s.part === part && s.index === index
}

function startDrag(event: PointerEvent, sel: Selection, mode: 'move' | 'resize' = 'move') {
  if (event.button !== 0) return
  event.stopPropagation()
  editor.selection = sel
  const input = draft.value.inputs[sel.key]
  drag = {
    sel,
    mode,
    start: point(event),
    box: sel.part === 'box' ? [...boxOf(sel)!] : null,
    anchor: input.anchor ? [...input.anchor] : null,
    remembered: false,
  }
  ;(event.currentTarget as Element).setPointerCapture(event.pointerId)
}

function onMove(event: PointerEvent) {
  if (splitDrag) {
    const dx = point(event)[0] - splitDrag.start
    if (!splitDrag.remembered) {
      if (Math.abs(dx) < 1) return
      remember()
      splitDrag.remembered = true
    }
    draft.value.split_at[splitDrag.index] = round(clamp(splitDrag.from + dx, 1, draft.value.size[0] - 1))
    return
  }
  if (!drag) return
  const [x, y] = point(event)
  const [dx, dy] = [x - drag.start[0], y - drag.start[1]]
  if (!drag.remembered) {
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
    remember()
    drag.remembered = true
  }
  const [W, H] = draft.value.size
  if (drag.sel.part === 'anchor' && drag.anchor) {
    draft.value.inputs[drag.sel.key].anchor = [round(clamp(drag.anchor[0] + dx, 0, W)), round(clamp(drag.anchor[1] + dy, 0, H))]
  } else if (drag.box && drag.mode === 'move') {
    const [bx, by, bw, bh] = drag.box
    setBox(drag.sel, [clamp(bx + dx, 0, W - bw), clamp(by + dy, 0, H - bh), bw, bh])
  } else if (drag.box) {
    const [bx, by, bw, bh] = drag.box
    setBox(drag.sel, [bx, by, clamp(bw + dx, MIN_BOX[0], W - bx), clamp(bh + dy, MIN_BOX[1], H - by)])
  }
}

function endDrag() {
  drag = null
  splitDrag = null
}

function onBackground(event: PointerEvent) {
  if (props.placing !== null) {
    addInput(props.placing || null, point(event))
    emit('placed')
  } else {
    editor.selection = null
  }
}

function onDrop(event: DragEvent) {
  const key = event.dataTransfer?.getData('application/x-hotas-input')
  if (key === undefined || !event.dataTransfer?.types.includes('application/x-hotas-input')) return
  event.preventDefault()
  addInput(key || null, point(event))
  emit('placed')
}

/** Point of the box nearest to the marker: where the leader line starts */
function lineStart(box: Box, anchor: [number, number]): [number, number] {
  const [x, y, w, h] = box
  return [clamp(anchor[0], x, x + w), clamp(anchor[1], y, y + h)]
}

const labelSize = (box: Box) => Math.min(12, Math.max(7, box[3] * 0.45))
defineExpose({ svg })
</script>

<template>
  <svg
    ref="svg"
    class="canvas"
    :class="{ placing: placing !== null }"
    :viewBox="`0 0 ${draft.size[0]} ${draft.size[1]}`"
    :width="draft.size[0] * editor.zoom"
    :height="draft.size[1] * editor.zoom"
    @pointerdown="onBackground"
    @pointermove="onMove"
    @pointerup="endDrag"
    @pointercancel="endDrag"
    @dragover.prevent
    @drop="onDrop"
  >
    <rect x="0" y="0" :width="draft.size[0]" :height="draft.size[1]" fill="#fff" />
    <image v-if="draft.image" :href="draft.image.dataUrl" x="0" y="0" :width="draft.size[0]" :height="draft.size[1]" preserveAspectRatio="xMidYMid meet" />
    <g v-for="(x, index) in draft.split_at" :key="`split-${index}`" class="split" @pointerdown="startSplitDrag($event, index)">
      <rect :x="x - 8" y="0" width="16" :height="draft.size[1]" class="split-grab" />
      <line :x1="x" y1="0" :x2="x" :y2="draft.size[1]" class="split-line" />
      <text :x="x + 6" y="16" class="split-label">découpe des pages</text>
    </g>
    <g v-for="key in keys" :key="key" class="input" :class="{ current: editor.selection?.key === key }">
      <template v-for="(box, index) in [draft.inputs[key].box, ...(draft.inputs[key].more_boxes ?? [])]" :key="index">
        <line
          v-if="draft.inputs[key].anchor && index === 0"
          :x1="lineStart(box, draft.inputs[key].anchor!)[0]"
          :y1="lineStart(box, draft.inputs[key].anchor!)[1]"
          :x2="draft.inputs[key].anchor![0]"
          :y2="draft.inputs[key].anchor![1]"
          class="leader"
        />
        <g class="box" :class="{ selected: isSelected(key, 'box', index) }" @pointerdown="startDrag($event, { key, part: 'box', index })">
          <rect :x="box[0]" :y="box[1]" :width="box[2]" :height="box[3]" rx="3" />
          <text :x="box[0] + 4" :y="box[1] + box[3] / 2 + labelSize(box) * 0.35" :font-size="labelSize(box)">
            {{ inputName(key) }}<tspan v-if="index > 0" class="extra"> (case {{ index + 1 }})</tspan>
          </text>
          <rect
            v-if="isSelected(key, 'box', index)"
            class="handle"
            :x="box[0] + box[2] - 5"
            :y="box[1] + box[3] - 5"
            width="10"
            height="10"
            @pointerdown="startDrag($event, { key, part: 'box', index }, 'resize')"
          />
        </g>
      </template>
      <circle
        v-if="draft.inputs[key].anchor"
        class="anchor"
        :class="{ selected: isSelected(key, 'anchor') }"
        :cx="draft.inputs[key].anchor![0]"
        :cy="draft.inputs[key].anchor![1]"
        r="6"
        @pointerdown="startDrag($event, { key, part: 'anchor', index: 0 })"
      />
    </g>
  </svg>
</template>

<style scoped>
.canvas { display: block; background: #fff; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); touch-action: none; user-select: none; }
.canvas.placing { cursor: crosshair; }
.box { cursor: move; }
.box rect:first-child { fill: rgba(255, 255, 255, 0.88); stroke: #1b1f24; stroke-width: 1; }
.box text { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; font-weight: 600; fill: #1b1f24; pointer-events: none; }
.box .extra { fill: #5d6570; }
.input.current .box rect:first-child { stroke: #e08e14; }
.box.selected rect:first-child { stroke: #e08e14; stroke-width: 2.5; fill: #fff8eb; }
.handle { fill: #e08e14; cursor: nwse-resize; }
.leader { stroke: #1b1f24; stroke-width: 1.2; pointer-events: none; }
.input.current .leader { stroke: #e08e14; }
.anchor { fill: #1b1f24; stroke: #fff; stroke-width: 2; cursor: grab; }
.anchor.selected, .input.current .anchor { fill: #e08e14; }
.split { cursor: ew-resize; }
.split-grab { fill: transparent; }
.split-line { stroke: #2f7de1; stroke-width: 2; stroke-dasharray: 10 6; }
.split-label { font: 600 12px 'Barlow Condensed', sans-serif; fill: #2f7de1; pointer-events: none; }
</style>
