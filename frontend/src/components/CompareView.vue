<template>
    <div class="p-6 max-w-screen-xl mx-auto">
      <h1 class="text-2xl font-bold mb-4">PDF Comparison Tool</h1>
      <form @submit.prevent="submitForm" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block font-semibold mb-1">Left PDF File:</label>
            <input type="file" @change="e => files.left = e.target.files[0]" required />
          </div>
          <div>
            <label class="block font-semibold mb-1">Right PDF File:</label>
            <input type="file" @change="e => files.right = e.target.files[0]" required />
          </div>
        </div>
  
        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Compare PDFs
        </button>
      </form>
  
      <div v-if="results.length" class="mt-10">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Comparison Result</h2>
          <div class="space-x-2">
            <button @click="downloadExcel" class="px-3 py-1 bg-green-600 text-white rounded">Download Excel</button>
            <button @click="downloadPDF" class="px-3 py-1 bg-red-600 text-white rounded">Download PDF</button>
          </div>
        </div>
  
        <div class="grid grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold mb-2">Left Document</h3>
            <div v-for="(result, index) in paginatedResults" :key="index">
              <div :class="getClass(result.type)">
                <p v-html="formatText(result.text_left_report)"></p>
              </div>
            </div>
          </div>
          <div>
            <h3 class="font-semibold mb-2">Right Document</h3>
            <div v-for="(result, index) in paginatedResults" :key="index">
              <div :class="getClass(result.type)">
                <p v-html="formatText(result.text_right_report)"></p>
              </div>
            </div>
          </div>
        </div>
  
        <div class="mt-6 flex justify-center space-x-2">
          <button @click="prevPage" :disabled="currentPage === 1" class="px-3 py-1 bg-gray-300 rounded">Previous</button>
          <span>Page {{ currentPage }} of {{ totalPages }}</span>
          <button @click="nextPage" :disabled="currentPage === totalPages" class="px-3 py-1 bg-gray-300 rounded">Next</button>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, computed } from 'vue'
  import axios from 'axios'
  import jsPDF from 'jspdf'
  import autoTable from 'jspdf-autotable'
  import * as XLSX from 'xlsx'
  
  const files = ref({ left: null, right: null })
  const results = ref([])
  const currentPage = ref(1)
  const pageSize = 10
  
  const paginatedResults = computed(() => {
    const start = (currentPage.value - 1) * pageSize
    return results.value.slice(start, start + pageSize)
  })
  
  const totalPages = computed(() => {
    return Math.ceil(results.value.length / pageSize)
  })
  
  const nextPage = () => {
    if (currentPage.value < totalPages.value) currentPage.value++
  }
  
  const prevPage = () => {
    if (currentPage.value > 1) currentPage.value--
  }
  
  const submitForm = async () => {
    const formData = new FormData()
    formData.append('left_file', files.value.left)
    formData.append('right_file', files.value.right)
    formData.append('header_left', 40)
    formData.append('footer_left', 40)
    formData.append('size_weight_left', 0.8)
    formData.append('header_right', 40)
    formData.append('footer_right', 40)
    formData.append('size_weight_right', 0.8)
    formData.append('ratio_threshold', 0.5)
    formData.append('length_threshold', 30)
  
    try {
      const res = await axios.post('http://localhost:8000/upload/', formData)
      results.value = res.data.comparison
      currentPage.value = 1
    } catch (err) {
      alert('Comparison failed: ' + err.message)
    }
  }
  
  const formatText = (text) => {
    if (typeof text === 'string') return text
    return text.map(t => `<span class="tag-${t.tag}">${t.subtext}</span>`).join('')
  }
  
  const getClass = (type) => {
    switch (type) {
      case 'equal': return 'bg-green-100 p-2 rounded'
      case 'insert': return 'bg-blue-100 p-2 rounded'
      case 'delete': return 'bg-red-100 p-2 rounded'
      case 'replace': return 'bg-yellow-100 p-2 rounded'
      default: return 'p-2 rounded border'
    }
  }
  
  const downloadExcel = () => {
    const rows = results.value.map((res, i) => [
      res.type,
      typeof res.text_left_report === 'string' ? res.text_left_report : res.text_left_report.map(t => t.subtext).join(''),
      typeof res.text_right_report === 'string' ? res.text_right_report : res.text_right_report.map(t => t.subtext).join('')
    ])
  
    const worksheet = XLSX.utils.aoa_to_sheet([
      ['Type', 'Left Text', 'Right Text'],
      ...rows
    ])
  
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Comparison')
    XLSX.writeFile(workbook, 'comparison_result.xlsx')
  }
  
  const downloadPDF = () => {
    const doc = new jsPDF()
    const rows = results.value.map((res) => [
      res.type,
      typeof res.text_left_report === 'string' ? res.text_left_report : res.text_left_report.map(t => t.subtext).join(''),
      typeof res.text_right_report === 'string' ? res.text_right_report : res.text_right_report.map(t => t.subtext).join('')
    ])
  
    autoTable(doc, {
      head: [['Type', 'Left Text', 'Right Text']],
      body: rows
    })
  
    doc.save('comparison_result.pdf')
  }
  </script>
  
  <style>
  .tag-insert {
    background-color: #e6ffed;
  }
  .tag-delete {
    background-color: #fee2e2;
  }
  .tag-replace {
    background-color: #fef9c3;
  }
  </style>